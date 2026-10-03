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
        / "production_chunk_metadata.json"
    )

    embeddings_path = (
        EMBEDDING_OUTPUT_DIR
        / "production_chunk_embeddings.npy"
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

def expand_evidence_context(
    evidence,
    metadata,
    top_sources=1,
    forward_chunks=2,
    max_words=2000,
):
    """
    Expand only the strongest reranked sources.

    For each selected result, include the retrieved
    chunk and following chunks from the same document.

    This avoids flooding the generation model with
    weaker neighbouring evidence.
    """

    expanded = []
    seen_vector_ids = set()
    total_words = 0

    # Only expand the strongest reranked results.
    selected_evidence = evidence[:top_sources]

    for result in selected_evidence:

        center_id = result["vector_id"]

        end_id = min(
            len(metadata),
            center_id + forward_chunks + 1,
        )

        for vector_id in range(
            center_id,
            end_id,
        ):

            if vector_id in seen_vector_ids:
                continue

            item = metadata[vector_id]

            # Stop when we leave this document.
            if (
                item["source_file"]
                != result["source_file"]
            ):
                break

            text = item["text"]

            word_count = len(
                text.split()
            )

            if (
                total_words + word_count
                > max_words
            ):
                return expanded

            expanded.append(
                {
                    "vector_id": vector_id,
                    "chunk_id": item["chunk_id"],
                    "source_file":
                        item["source_file"],
                    "file_type":
                        item["file_type"],
                    "page_number":
                        item.get("page_number"),
                    "slide_number":
                        item.get("slide_number"),
                    "text": text,
                }
            )

            seen_vector_ids.add(
                vector_id
            )

            total_words += word_count

    return expanded

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
You are a document question-answering assistant.

USER QUESTION:
{question}

DOCUMENT EVIDENCE:
{context}

TASK:
Give a direct answer to the USER QUESTION using only
information explicitly stated in the DOCUMENT EVIDENCE.

Rules:
- Answer the USER QUESTION exactly as written.
- Do not change or reinterpret the question.
- Use only information explicitly present in the evidence.
- Ignore evidence that is not useful for answering the question.
- Do not use outside knowledge.
- Do not invent facts, exercises, recommendations, numbers,
  explanations, or conclusions.
- Do not write citations, source numbers, document names,
  page numbers, or slide numbers. The application will add
  source information separately.
- Do not discuss what the documents are missing.
- Do not recommend further research or professional guidance.
- For a "how" question, give useful actions explicitly
  supported by the evidence.
- Include useful details such as durations or repetitions
  when they are explicitly stated in the evidence.
- Keep the answer concise and factual.

If the evidence does not contain useful information for
answering the USER QUESTION, respond exactly:

"The available documents do not provide enough information to answer this question."

USER QUESTION AGAIN:
{question}

ANSWER:
""".strip()

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
            },
        },
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "response",
        ""
    ).strip()

def build_trusted_sources(expanded_evidence):
    """
    Build source citations directly from trusted metadata.

    Citations are created by Python rather than the LLM so
    filenames and page/slide numbers cannot be invented.
    """

    sources = []
    seen = set()

    for item in expanded_evidence:
        if item["file_type"] == "pdf":
            location = (
                f"Page {item['page_number']}"
            )
        else:
            location = (
                f"Slide {item['slide_number']}"
            )

        source_key = (
            item["source_file"],
            location,
        )

        if source_key in seen:
            continue

        seen.add(source_key)

        sources.append(
            {
                "document": item["source_file"],
                "location": location,
            }
        )

    return sources

def verify_refusal(
    question,
    evidence,
):
    """
    Second-pass verification used only when the
    first generation attempt refuses to answer.

    It checks all retrieved evidence before
    accepting the refusal.
    """

    if not evidence:
        return None

    evidence_parts = []

    for index, item in enumerate(
        evidence,
        start=1,
    ):
        if item["file_type"] == "pdf":
            location = (
                f"Page {item['page_number']}"
            )
        else:
            location = (
                f"Slide {item['slide_number']}"
            )

        evidence_parts.append(
            f"""
SOURCE {index}
Document: {item['source_file']}
Location: {location}

Content:
{item['text']}
""".strip()
        )

    combined_evidence = "\n\n".join(
        evidence_parts
    )

    verification_prompt = f"""
Answer the USER QUESTION using ONLY the DOCUMENT EVIDENCE below.

USER QUESTION:
{question}

DOCUMENT EVIDENCE:
{combined_evidence}

TASK:
Answer the USER QUESTION directly using only the DOCUMENT EVIDENCE.

Rules:
- Read all DOCUMENT EVIDENCE before answering.
- First look for sentences that directly answer the question.
- If the question asks for exercises, identify exercises explicitly
  described in the evidence.
- If the question asks "how", identify actions or recommendations
  explicitly described in the evidence.
- Use only information explicitly present in the evidence.
- Do not use outside knowledge.
- Do not invent facts.
- Do not write citations, source numbers, document names,
  page numbers, or slide numbers.
- Do not discuss whether the evidence is complete.
- Do not discuss information that is missing.
- If at least one useful fact, exercise, action, or recommendation
  answers the question, provide it.
- Include useful details such as duration, repetitions, or technique
  when explicitly stated.
- Keep the answer concise and factual.

Only if NONE of the DOCUMENT EVIDENCE contains information
that answers the USER QUESTION, respond exactly:

"The available documents do not provide enough information to answer this question."

USER QUESTION AGAIN:
{question}

ANSWER:
""".strip()

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL_NAME,
            "prompt": verification_prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
            },
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

    verification_refusal = (
        "the available documents do not provide enough information"
    )

    if (
        not verification_answer
        or verification_answer.lower().startswith(
            verification_refusal
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

        expanded_evidence = (
            expand_evidence_context(
                evidence=evidence,
                metadata=metadata,
            )
        )

        context = build_context(
            expanded_evidence
        )

        trusted_sources = build_trusted_sources(
            expanded_evidence
        )

        print(
            f"Expanded context chunks: "
            f"{len(expanded_evidence)}"
        )

        print(
            f"Expanded context words: "
            f"{sum(len(item['text'].split()) for item in expanded_evidence)}"
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
                    expanded_evidence,
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

        if not answer.lower().startswith(refusal_phrase):
            print()
            print("Sources:")
            for source in trusted_sources:
                print(f"- {source}")

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