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
    OLLAMA_MODEL_NAME,
    OLLAMA_URL,
)


CANDIDATE_K = 15
FINAL_CONTEXT_K = 4

SEMANTIC_WEIGHT = 0.70
BM25_WEIGHT = 0.30


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def tokenize(text):
    return re.findall(r"\b\w+\b", text.lower())


def min_max_normalize(values):
    values = np.asarray(values, dtype=np.float32)

    if len(values) == 0:
        return values

    minimum = values.min()
    maximum = values.max()

    if maximum == minimum:
        return np.zeros_like(values)

    return (values - minimum) / (maximum - minimum)


def load_resources():
    metadata_path = (
        EMBEDDING_OUTPUT_DIR
        / "chunk_metadata.json"
    )

    embeddings_path = (
        EMBEDDING_OUTPUT_DIR
        / "chunk_embeddings.npy"
    )

    metadata = load_json(metadata_path)

    embeddings = np.load(
        embeddings_path
    ).astype("float32")

    return metadata, embeddings


def build_bm25(metadata):
    tokenized_corpus = [
        tokenize(item["text"])
        for item in metadata
    ]

    return BM25Okapi(tokenized_corpus)


def get_hybrid_candidates(
    query,
    embedding_model,
    metadata,
    embeddings,
    bm25,
    top_k=CANDIDATE_K,
):
    query_embedding = embedding_model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")[0]

    semantic_scores = (
        embeddings
        @ query_embedding
    )

    semantic_scores = min_max_normalize(
        semantic_scores
    )

    bm25_scores = bm25.get_scores(
        tokenize(query)
    )

    bm25_scores = min_max_normalize(
        bm25_scores
    )

    combined_scores = (
        SEMANTIC_WEIGHT
        * semantic_scores
        +
        BM25_WEIGHT
        * bm25_scores
    )

    top_indices = np.argsort(
        combined_scores
    )[::-1][:top_k]

    candidates = []

    for vector_id in top_indices:
        item = metadata[int(vector_id)]

        candidates.append(
            {
                "vector_id": int(vector_id),
                "hybrid_score": float(
                    combined_scores[vector_id]
                ),
                "chunk_id": item["chunk_id"],
                "source_file": item["source_file"],
                "file_type": item["file_type"],
                "page_number": item.get(
                    "page_number"
                ),
                "slide_number": item.get(
                    "slide_number"
                ),
                "text": item["text"],
            }
        )

    return candidates


def rerank_candidates(
    query,
    candidates,
    reranker,
    top_k=FINAL_CONTEXT_K,
):
    pairs = [
        [query, candidate["text"]]
        for candidate in candidates
    ]

    scores = reranker.predict(pairs)

    for candidate, score in zip(
        candidates,
        scores,
    ):
        candidate["reranker_score"] = (
            float(score)
        )

    candidates = sorted(
        candidates,
        key=lambda item:
            item["reranker_score"],
        reverse=True,
    )

    return candidates[:top_k]


def build_context(results):
    context_parts = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        if result["file_type"] == "pdf":
            location = (
                f"Page {result['page_number']}"
            )
        else:
            location = (
                f"Slide {result['slide_number']}"
            )

        context_parts.append(
            f"""
SOURCE {index}
Document: {result['source_file']}
Location: {location}
Chunk ID: {result['chunk_id']}

Content:
{result['text']}
""".strip()
        )

    return "\n\n".join(context_parts)


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

    data = response.json()

    return data.get(
        "response",
        ""
    ).strip()

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

def main():
    print()
    print("=" * 80)
    print(
        "TENNIS EXPLORE - V2 "
        "RAG ANSWER GENERATION"
    )
    print("=" * 80)

    print()
    print(
        f"Loading embedding model: "
        f"{EMBEDDING_MODEL_NAME}"
    )

    embedding_model = (
        SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )
    )

    print(
        f"Loading reranker model: "
        f"{RERANKER_MODEL_NAME}"
    )

    reranker = CrossEncoder(
        RERANKER_MODEL_NAME
    )

    metadata, embeddings = (
        load_resources()
    )

    bm25 = build_bm25(metadata)

    print(
        f"Chunks loaded: {len(metadata)}"
    )

    while True:
        print()

        question = input(
            "Enter a question "
            "(or type 'exit'): "
        ).strip()

        if question.lower() in {
            "exit",
            "quit",
            "q",
        }:
            print("Finished.")
            break

        if not question:
            continue

        candidates = (
            get_hybrid_candidates(
                question,
                embedding_model,
                metadata,
                embeddings,
                bm25,
            )
        )

        evidence = rerank_candidates(
            question,
            candidates,
            reranker,
        )

        context = build_context(
            evidence
        )

        print()
        print(
            "Generating answer..."
        )

        try:
            answer = generate_answer(
                question,
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
                    question,
                    evidence,
                )

                if verified_answer:
                    answer = verified_answer

        except requests.exceptions.ConnectionError:
            print()
            print(
                "Could not connect to Ollama."
            )
            print(
                "Make sure Ollama is running."
            )
            continue

        except Exception as exc:
            print(
                f"Generation failed: {exc}"
            )
            continue

        print()
        print("=" * 80)
        print("ANSWER")
        print("=" * 80)
        print()
        print(answer)

        print()
        print("=" * 80)
        print("RETRIEVED EVIDENCE")
        print("=" * 80)

        for index, item in enumerate(
            evidence,
            start=1,
        ):
            print()

            if item["file_type"] == "pdf":
                location = (
                    f"Page {item['page_number']}"
                )
            else:
                location = (
                    f"Slide {item['slide_number']}"
                )

            print(
                f"{index}. "
                f"{item['source_file']} "
                f"- {location}"
            )

            print(
                f"   Reranker score: "
                f"{item['reranker_score']:.4f}"
            )


if __name__ == "__main__":
    main()