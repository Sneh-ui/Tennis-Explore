import json
import re
import sys
from pathlib import Path

import numpy as np
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
)


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

CANDIDATE_K = 15
FINAL_TOP_K = 5

SEMANTIC_WEIGHT = 0.70
BM25_WEIGHT = 0.30


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def load_json(path):
    with path.open("r", encoding="utf-8") as file:
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


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

def load_resources():

    metadata_path = (
        EMBEDDING_OUTPUT_DIR
        / "production_chunk_metadata.json"
    )

    embeddings_path = (
        EMBEDDING_OUTPUT_DIR
        / "production_chunk_embeddings.npy"
    )

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata not found: {metadata_path}"
        )

    if not embeddings_path.exists():
        raise FileNotFoundError(
            f"Embeddings not found: {embeddings_path}"
        )

    metadata = load_json(
        metadata_path
    )

    embeddings = np.load(
        embeddings_path
    ).astype("float32")

    if len(metadata) != len(embeddings):
        raise ValueError(
            "Metadata and embeddings do not match."
        )

    return metadata, embeddings


# ---------------------------------------------------------
# BM25
# ---------------------------------------------------------

def build_bm25(metadata):

    tokenized_corpus = [
        tokenize(item["text"])
        for item in metadata
    ]

    return BM25Okapi(
        tokenized_corpus
    )


# ---------------------------------------------------------
# HYBRID CANDIDATE RETRIEVAL
# ---------------------------------------------------------

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

    semantic_scores = (
        min_max_normalize(
            semantic_scores
        )
    )

    query_tokens = tokenize(query)

    bm25_scores = bm25.get_scores(
        query_tokens
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

        item = metadata[
            int(vector_id)
        ]

        candidates.append(
            {
                "vector_id":
                    int(vector_id),

                "hybrid_score":
                    float(
                        combined_scores[
                            vector_id
                        ]
                    ),

                "semantic_score":
                    float(
                        semantic_scores[
                            vector_id
                        ]
                    ),

                "bm25_score":
                    float(
                        bm25_scores[
                            vector_id
                        ]
                    ),

                "chunk_id":
                    item["chunk_id"],

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

                "text":
                    item["text"],
            }
        )

    return candidates


# ---------------------------------------------------------
# RERANK
# ---------------------------------------------------------

def rerank_candidates(
    query,
    candidates,
    reranker,
    top_k=FINAL_TOP_K,
):

    pairs = [
        [
            query,
            candidate["text"],
        ]
        for candidate in candidates
    ]

    reranker_scores = (
        reranker.predict(
            pairs
        )
    )

    for candidate, score in zip(
        candidates,
        reranker_scores,
    ):
        candidate[
            "reranker_score"
        ] = float(score)

    candidates = sorted(
        candidates,
        key=lambda item:
            item["reranker_score"],
        reverse=True,
    )

    return candidates[:top_k]


# ---------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------

def print_results(
    query,
    results,
):

    print()
    print("=" * 80)
    print(
        "HYBRID + RERANKER RESULTS"
    )
    print("=" * 80)

    print()
    print(f"Query: {query}")

    for rank, result in enumerate(
        results,
        start=1,
    ):

        print()
        print("-" * 80)

        print(
            f"Rank      : {rank}"
        )

        print(
            f"Reranker  : "
            f"{result['reranker_score']:.4f}"
        )

        print(
            f"Hybrid    : "
            f"{result['hybrid_score']:.4f}"
        )

        print(
            f"Semantic  : "
            f"{result['semantic_score']:.4f}"
        )

        print(
            f"BM25      : "
            f"{result['bm25_score']:.4f}"
        )

        print(
            f"Source    : "
            f"{result['source_file']}"
        )

        if (
            result["file_type"]
            == "pdf"
        ):
            print(
                f"Page      : "
                f"{result['page_number']}"
            )

        elif (
            result["file_type"]
            == "pptx"
        ):
            print(
                f"Slide     : "
                f"{result['slide_number']}"
            )

        print(
            f"Chunk     : "
            f"{result['chunk_id']}"
        )

        print()
        print("Text:")

        preview = (
            result["text"][:500]
        )

        print(preview)

        if len(
            result["text"]
        ) > 500:
            print("...")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print()
    print("=" * 80)
    print(
        "TENNIS EXPLORE - V2 "
        "HYBRID + RERANKING"
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

    print()
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

    bm25 = build_bm25(
        metadata
    )

    print()
    print(
        f"Chunks loaded: "
        f"{len(metadata)}"
    )

    while True:

        print()

        query = input(
            "Enter a question "
            "(or type 'exit'): "
        ).strip()

        if query.lower() in {
            "exit",
            "quit",
            "q",
        }:
            print(
                "Search finished."
            )
            break

        if not query:
            continue

        candidates = (
            get_hybrid_candidates(
                query=query,
                embedding_model=
                    embedding_model,
                metadata=metadata,
                embeddings=embeddings,
                bm25=bm25,
                top_k=CANDIDATE_K,
            )
        )

        print()
        print("=" * 80)
        print("TOP 15 BEFORE RERANKING")
        print("=" * 80)

        for rank, candidate in enumerate(
            candidates,
            start=1,
        ):
            print(
                f"{rank:2d}. "
                f"Hybrid={candidate['hybrid_score']:.4f} | "
                f"{candidate['source_file']} | "
                f"{candidate['chunk_id']}"
            )

        results = rerank_candidates(
            query=query,
            candidates=candidates,
            reranker=reranker,
            top_k=FINAL_TOP_K,
        )

        print_results(
            query,
            results,
        )


if __name__ == "__main__":
    main()