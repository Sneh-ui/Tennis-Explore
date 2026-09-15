import json
import re
import sys
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------
# PROJECT CONFIG
# ---------------------------------------------------------

CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import (
    EMBEDDING_MODEL_NAME,
    EMBEDDING_OUTPUT_DIR,
    FAISS_OUTPUT_DIR,
)


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

TOP_K = 5

# Initial baseline weights.
# We will evaluate these rather than assuming they are optimal.
SEMANTIC_WEIGHT = 0.70
BM25_WEIGHT = 0.30


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def tokenize(text):
    """
    Simple BM25 tokenization.

    Converts to lowercase and keeps words/numbers.
    """
    return re.findall(
        r"\b\w+\b",
        text.lower(),
    )


def min_max_normalize(values):
    """
    Convert an array of scores to the range 0-1.

    This is necessary because FAISS similarity scores
    and BM25 scores use different scales.
    """

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
# LOAD RESOURCES
# ---------------------------------------------------------

def load_resources():

    faiss_path = (
        FAISS_OUTPUT_DIR
        / "documents_v2.index"
    )

    metadata_path = (
        EMBEDDING_OUTPUT_DIR
        / "chunk_metadata.json"
    )

    embeddings_path = (
        EMBEDDING_OUTPUT_DIR
        / "chunk_embeddings.npy"
    )

    if not faiss_path.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {faiss_path}"
        )

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata not found: {metadata_path}"
        )

    if not embeddings_path.exists():
        raise FileNotFoundError(
            f"Embeddings not found: {embeddings_path}"
        )

    index = faiss.read_index(
        str(faiss_path)
    )

    metadata = load_json(
        metadata_path
    )

    embeddings = np.load(
        embeddings_path
    ).astype("float32")

    if len(metadata) != len(embeddings):
        raise ValueError(
            "Metadata and embedding counts do not match."
        )

    return (
        index,
        metadata,
        embeddings,
    )


# ---------------------------------------------------------
# BUILD BM25 INDEX
# ---------------------------------------------------------

def build_bm25(metadata):

    tokenized_corpus = [
        tokenize(item["text"])
        for item in metadata
    ]

    bm25 = BM25Okapi(
        tokenized_corpus
    )

    return bm25


# ---------------------------------------------------------
# HYBRID SEARCH
# ---------------------------------------------------------

def hybrid_search(
    query,
    model,
    index,
    metadata,
    embeddings,
    bm25,
    top_k=TOP_K,
):

    # -----------------------------------------------------
    # SEMANTIC QUERY EMBEDDING
    # -----------------------------------------------------

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")


    # -----------------------------------------------------
    # SEMANTIC SCORES FOR ALL VECTORS
    # -----------------------------------------------------

    # Because the vectors are normalized and the FAISS
    # index uses inner product, this acts like cosine
    # similarity.

    semantic_scores = (
        embeddings
        @ query_embedding[0]
    )

    semantic_normalized = (
        min_max_normalize(
            semantic_scores
        )
    )


    # -----------------------------------------------------
    # BM25 SCORES
    # -----------------------------------------------------

    query_tokens = tokenize(query)

    bm25_scores = (
        bm25.get_scores(
            query_tokens
        )
    )

    bm25_normalized = (
        min_max_normalize(
            bm25_scores
        )
    )


    # -----------------------------------------------------
    # COMBINE SCORES
    # -----------------------------------------------------

    combined_scores = (
        SEMANTIC_WEIGHT
        * semantic_normalized
        +
        BM25_WEIGHT
        * bm25_normalized
    )


    # -----------------------------------------------------
    # GET TOP RESULTS
    # -----------------------------------------------------

    top_indices = np.argsort(
        combined_scores
    )[::-1][:top_k]

    results = []

    for rank, vector_id in enumerate(
        top_indices,
        start=1,
    ):

        item = metadata[
            int(vector_id)
        ]

        results.append(
            {
                "rank": rank,
                "combined_score":
                    float(
                        combined_scores[
                            vector_id
                        ]
                    ),
                "semantic_score":
                    float(
                        semantic_normalized[
                            vector_id
                        ]
                    ),
                "bm25_score":
                    float(
                        bm25_normalized[
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

    return results


# ---------------------------------------------------------
# DISPLAY RESULTS
# ---------------------------------------------------------

def print_results(
    query,
    results,
):

    print()
    print("=" * 80)
    print(
        "HYBRID SEARCH RESULTS"
    )
    print("=" * 80)

    print()
    print(f"Query: {query}")

    print(
        f"Weights: semantic="
        f"{SEMANTIC_WEIGHT:.2f}, "
        f"BM25={BM25_WEIGHT:.2f}"
    )

    for result in results:

        print()
        print("-" * 80)

        print(
            f"Rank      : "
            f"{result['rank']}"
        )

        print(
            f"Combined  : "
            f"{result['combined_score']:.4f}"
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

        preview = (
            result["text"][:500]
        )

        print()
        print("Text:")
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
        "HYBRID RETRIEVAL"
    )
    print("=" * 80)

    print()
    print(
        f"Loading embedding model: "
        f"{EMBEDDING_MODEL_NAME}"
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    (
        index,
        metadata,
        embeddings,
    ) = load_resources()

    print()
    print(
        f"Vectors loaded: "
        f"{index.ntotal}"
    )

    print(
        f"Metadata records: "
        f"{len(metadata)}"
    )

    print()
    print(
        "Building BM25 index..."
    )

    bm25 = build_bm25(
        metadata
    )

    print(
        "BM25 index ready."
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

        results = hybrid_search(
            query=query,
            model=model,
            index=index,
            metadata=metadata,
            embeddings=embeddings,
            bm25=bm25,
            top_k=TOP_K,
        )

        print_results(
            query,
            results,
        )


if __name__ == "__main__":
    main()