import csv
import json
import re
import sys
from pathlib import Path

import numpy as np
import requests
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder


CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import (
    EMBEDDING_MODEL_NAME,
    RERANKER_MODEL_NAME,
    EMBEDDING_OUTPUT_DIR,
    OUTPUT_DIR,
    OLLAMA_MODEL_NAME,
    OLLAMA_URL,
)


CANDIDATE_K = 15
FINAL_CONTEXT_K = 4

SEMANTIC_WEIGHT = 0.70
BM25_WEIGHT = 0.30


EVALUATION_DIR = OUTPUT_DIR / "evaluation"

EVALUATION_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_CSV = (
    EVALUATION_DIR
    / "evaluation_results.csv"
)

RESULTS_JSON = (
    EVALUATION_DIR
    / "evaluation_results.json"
)

QUESTIONS_PATH = (
    CURRENT_FILE.parent
    / "evaluation_questions.json"
)


def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def tokenize(text):
    return re.findall(
        r"\b\w+\b",
        text.lower(),
    )


def min_max_normalize(values):
    values = np.asarray(
        values,
        dtype=np.float32,
    )

    if len(values) == 0:
        return values

    minimum = values.min()
    maximum = values.max()

    if maximum == minimum:
        return np.zeros_like(values)

    return (
        (values - minimum)
        / (maximum - minimum)
    )


def load_resources():
    metadata = load_json(
        EMBEDDING_OUTPUT_DIR
        / "chunk_metadata.json"
    )

    embeddings = np.load(
        EMBEDDING_OUTPUT_DIR
        / "chunk_embeddings.npy"
    ).astype("float32")

    return metadata, embeddings


def build_bm25(metadata):
    corpus = [
        tokenize(item["text"])
        for item in metadata
    ]

    return BM25Okapi(corpus)


def get_hybrid_candidates(
    query,
    embedding_model,
    metadata,
    embeddings,
    bm25,
):
    query_embedding = (
        embedding_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        .astype("float32")[0]
    )

    semantic_scores = (
        embeddings
        @ query_embedding
    )

    semantic_scores = (
        min_max_normalize(
            semantic_scores
        )
    )

    bm25_scores = (
        bm25.get_scores(
            tokenize(query)
        )
    )

    bm25_scores = (
        min_max_normalize(
            bm25_scores
        )
    )

    combined_scores = (
        SEMANTIC_WEIGHT
        * semantic_scores
        +
        BM25_WEIGHT
        * bm25_scores
    )

    top_indices = (
        np.argsort(
            combined_scores
        )[::-1][:CANDIDATE_K]
    )

    candidates = []

    for index in top_indices:
        item = metadata[int(index)]

        candidates.append(
            {
                "source_file":
                    item["source_file"],
                "file_type":
                    item["file_type"],
                "page_number":
                    item.get(
                        "page_number"
                    ),
                "slide_number":
                    item.get(
                        "slide_number"
                    ),
                "chunk_id":
                    item["chunk_id"],
                "text":
                    item["text"],
                "hybrid_score":
                    float(
                        combined_scores[
                            index
                        ]
                    ),
            }
        )

    return candidates


def rerank(
    query,
    candidates,
    reranker,
):
    pairs = [
        [
            query,
            item["text"],
        ]
        for item in candidates
    ]

    scores = reranker.predict(
        pairs
    )

    for item, score in zip(
        candidates,
        scores,
    ):
        item["reranker_score"] = (
            float(score)
        )

    return sorted(
        candidates,
        key=lambda x:
            x["reranker_score"],
        reverse=True,
    )[:FINAL_CONTEXT_K]


def build_context(evidence):
    parts = []

    for index, item in enumerate(
        evidence,
        start=1,
    ):
        if (
            item["file_type"]
            == "pdf"
        ):
            location = (
                f"Page "
                f"{item['page_number']}"
            )
        else:
            location = (
                f"Slide "
                f"{item['slide_number']}"
            )

        parts.append(
            f"""
SOURCE {index}
Document: {item['source_file']}
Location: {location}

Content:
{item['text']}
""".strip()
        )

    return "\n\n".join(parts)


def generate_answer(
    question,
    context,
):
    prompt = f"""
You are answering questions using retrieved document evidence.

IMPORTANT:
The document evidence below has already been retrieved from the project documents.
Some retrieved sources may be irrelevant. Ignore irrelevant sources.

Follow these rules carefully:

1. Answer using ONLY the supplied document evidence.
2. Do NOT use outside knowledge.
3. Check whether ANY supplied source directly or reasonably answers the question.
4. If even one source contains the answer, answer the question directly.
5. NEVER say there is insufficient information when a supplied source explicitly contains the requested fact.
6. For questions asking for a number, percentage, temperature, threshold, date, count, or other factual value:
   - preserve the value exactly as stated in the evidence;
   - do not reinterpret the question;
   - do not invent a different threshold or value.
7. Ignore retrieved sources that are unrelated to the question.
8. Prefer evidence that most directly answers the question.
9. Keep the answer concise and factual.
10. Cite the document and page or slide containing the evidence.
11. Do not invent facts, conclusions, page numbers, slide numbers, or citations.

Only when NONE of the supplied evidence contains information that can answer the question, respond exactly:

"The available documents do not provide enough information to answer this question."

QUESTION:
{question}

RETRIEVED DOCUMENT EVIDENCE:
{context}

Before answering, determine:
- Does any source explicitly contain the requested answer?
- If yes, use that evidence and answer directly.
- If no, use the insufficient-information response.

ANSWER:
""".strip()

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL_NAME,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )

    response.raise_for_status()

    return (
        response.json()
        .get(
            "response",
            "",
        )
        .strip()
    )

def verify_refusal(
    question,
    evidence,
):
    """
    Second-pass check used only when the first
    generation attempt refuses to answer.

    It checks the strongest retrieved evidence
    directly before accepting the refusal.
    """

    if not evidence:
        return None

    # Use the strongest retrieved chunk only.
    best = evidence[0]

    if best["file_type"] == "pdf":
        location = (
            f"Page {best['page_number']}"
        )
    else:
        location = (
            f"Slide {best['slide_number']}"
        )

    verification_prompt = f"""
Check whether the evidence below directly answers the question.

Use ONLY the evidence provided.

QUESTION:
{question}

EVIDENCE:
Document: {best['source_file']}
Location: {location}

{best['text']}

Instructions:

1. Look carefully for an explicit statement that answers the question.
2. If the answer is explicitly present, return ONLY the concise answer and cite the document and location.
3. Preserve numbers, percentages, temperatures, names, and other factual values exactly.
4. Do not use outside knowledge.
5. If the evidence does NOT answer the question, respond exactly:

NOT_FOUND

ANSWER:
""".strip()

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL_NAME,
            "prompt": verification_prompt,
            "stream": False,
        },
        timeout=120,
    )

    response.raise_for_status()

    verification_answer = (
        response.json()
        .get(
            "response",
            "",
        )
        .strip()
    )

    if (
        not verification_answer
        or verification_answer.upper().startswith(
            "NOT_FOUND"
        )
    ):
        return None

    return verification_answer

def evaluate_question(
    test,
    evidence,
    answer,
):
    expected_source = test.get(
        "expected_source"
    )

    expected_page = test.get(
        "expected_page"
    )

    expected_slide = test.get(
        "expected_slide"
    )

    should_refuse = test.get(
        "should_refuse",
        False,
    )

    top_source = None
    top_page = None
    top_slide = None

    if evidence:
        top_source = evidence[0][
            "source_file"
        ]

        top_page = evidence[0].get(
            "page_number"
        )

        top_slide = evidence[0].get(
            "slide_number"
        )

    source_match = (
        expected_source is not None
        and top_source == expected_source
    )

    expected_in_top_k = False
    location_in_top_k = False

    for item in evidence:

        if (
            expected_source
            and item["source_file"]
            == expected_source
        ):
            expected_in_top_k = True

            # PDF evaluation
            if expected_page is not None:
                if (
                    item.get("page_number")
                    == expected_page
                ):
                    location_in_top_k = True

            # PPTX evaluation
            elif expected_slide is not None:
                if (
                    item.get("slide_number")
                    == expected_slide
                ):
                    location_in_top_k = True

            # No specific page/slide required
            else:
                location_in_top_k = True

    clean_answer = (
        answer.lower().strip()
    )

    # Normalize whitespace so small formatting differences
    # from the language model do not cause false failures.
    normalized_answer = re.sub(
        r"\s+",
        " ",
        clean_answer,
    )

    refusal_patterns = [
        r"^the available documents do not provide enough\s*information to answer",
        r"^the documents do not provide enough\s*information to answer",
    ]

    refused = any(
        re.search(
            pattern,
            normalized_answer,
        )
        is not None
        for pattern in refusal_patterns
    )

    if should_refuse:
        passed = refused

    else:
        passed = (
            expected_in_top_k
            and location_in_top_k
            and not refused
        )

    return {
        "id":
            test["id"],

        "question":
            test["question"],

        "expected_source":
            expected_source,

        "expected_page":
            expected_page,

        "expected_slide":
            expected_slide,

        "top_source":
            top_source,

        "top_page":
            top_page,

        "top_slide":
            top_slide,

        "top_source_match":
            source_match,

        "expected_source_in_top4":
            expected_in_top_k,

        "expected_location_in_top4":
            location_in_top_k,

        "should_refuse":
            should_refuse,

        "refused":
            refused,

        "pass":
            passed,

        "answer":
            answer,
    }


def save_results(
    results,
):
    with RESULTS_JSON.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )

    fieldnames = [
        "id",
        "question",
        "expected_source",
        "expected_page",
        "expected_slide",
        "top_source",
        "top_page",
        "top_slide",
        "top_source_match",
        "expected_source_in_top4",
        "expected_location_in_top4",
        "should_refuse",
        "refused",
        "pass",
    ]

    with RESULTS_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    key:
                        result.get(key)
                    for key
                    in fieldnames
                }
            )


def print_summary(results):
    passed = sum(
        1
        for result in results
        if result["pass"]
    )

    total = len(results)

    percentage = (
        (passed / total) * 100
        if total
        else 0
    )

    print()
    print("=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    for result in results:
        status = (
            "PASS"
            if result["pass"]
            else "FAIL"
        )

        print(
            f"{result['id']} "
            f"- {status}"
        )

    print()
    print(
        f"Passed: "
        f"{passed}/{total}"
    )

    print(
        f"Success rate: "
        f"{percentage:.1f}%"
    )

    print()
    print(
        f"CSV saved to: "
        f"{RESULTS_CSV}"
    )

    print(
        f"JSON saved to: "
        f"{RESULTS_JSON}"
    )


def main():
    print()
    print("=" * 70)
    print(
        "TENNIS EXPLORE - "
        "V2 PIPELINE EVALUATION"
    )
    print("=" * 70)

    tests = load_json(
        QUESTIONS_PATH
    )

    print(
        f"Evaluation questions: "
        f"{len(tests)}"
    )

    embedding_model = (
        SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )
    )

    reranker = CrossEncoder(
        RERANKER_MODEL_NAME
    )

    metadata, embeddings = (
        load_resources()
    )

    bm25 = build_bm25(
        metadata
    )

    results = []

    for test in tests:
        print()
        print(
            f"Testing "
            f"{test['id']}: "
            f"{test['question']}"
        )

        candidates = (
            get_hybrid_candidates(
                test["question"],
                embedding_model,
                metadata,
                embeddings,
                bm25,
            )
        )

        evidence = rerank(
            test["question"],
            candidates,
            reranker,
        )

        context = build_context(
            evidence
        )

        answer = generate_answer(
            test["question"],
            context,
        )

        refusal_phrase = (
            "the available documents do not "
            "provide enough information"
        )

        if answer.lower().startswith(
            refusal_phrase
        ):
            verified_answer = verify_refusal(
                test["question"],
                evidence,
            )

            if verified_answer:
                answer = verified_answer

        result = (
            evaluate_question(
                test,
                evidence,
                answer,
            )
        )

        results.append(
            result
        )

        print(
            "Result: "
            + (
                "PASS"
                if result["pass"]
                else "FAIL"
            )
        )

    save_results(
        results
    )

    print_summary(
        results
    )


if __name__ == "__main__":
    main()