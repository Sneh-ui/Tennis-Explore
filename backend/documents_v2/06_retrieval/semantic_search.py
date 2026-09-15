import json
import sys
from pathlib import Path

import faiss
import numpy as np
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


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_resources():

    faiss_path = (
        FAISS_OUTPUT_DIR
        / "documents_v2.index"
    )

    metadata_path = (
        EMBEDDING_OUTPUT_DIR
        / "chunk_metadata.json"
    )

    if not faiss_path.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {faiss_path}"
        )

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata not found: {metadata_path}"
        )

    index = faiss.read_index(
        str(faiss_path)
    )

    metadata = load_json(
        metadata_path
    )

    return index, metadata


# ---------------------------------------------------------
# SEARCH
# ---------------------------------------------------------

def semantic_search(
    query,
    model,
    index,
    metadata,
    top_k=TOP_K,
):

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    query_embedding = (
        query_embedding.astype("float32")
    )

    scores, indices = index.search(
        query_embedding,
        top_k,
    )

    results = []

    for rank, (
        vector_id,
        score,
    ) in enumerate(
        zip(indices[0], scores[0]),
        start=1,
    ):

        if vector_id == -1:
            continue

        item = metadata[
            int(vector_id)
        ]

        results.append(
            {
                "rank": rank,
                "score": float(score),
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
# DISPLAY
# ---------------------------------------------------------

def print_results(
    query,
    results,
):

    print()
    print("=" * 80)
    print("SEMANTIC SEARCH RESULTS")
    print("=" * 80)

    print()
    print(f"Query: {query}")

    for result in results:

        print()
        print("-" * 80)

        print(
            f"Rank   : "
            f"{result['rank']}"
        )

        print(
            f"Score  : "
            f"{result['score']:.4f}"
        )

        print(
            f"Source : "
            f"{result['source_file']}"
        )

        if (
            result["file_type"]
            == "pdf"
        ):
            print(
                f"Page   : "
                f"{result['page_number']}"
            )

        elif (
            result["file_type"]
            == "pptx"
        ):
            print(
                f"Slide  : "
                f"{result['slide_number']}"
            )

        print(
            f"Chunk  : "
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
        "SEMANTIC RETRIEVAL"
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

    index, metadata = (
        load_resources()
    )

    print()
    print(
        f"FAISS vectors loaded: "
        f"{index.ntotal}"
    )

    print(
        f"Metadata records loaded: "
        f"{len(metadata)}"
    )

    while True:

        print()
        query = input(
            "Enter a question "
            "(or type 'exit'): "
        ).strip()

        if (
            query.lower()
            in {
                "exit",
                "quit",
                "q",
            }
        ):
            print(
                "Search finished."
            )
            break

        if not query:
            continue

        results = semantic_search(
            query=query,
            model=model,
            index=index,
            metadata=metadata,
            top_k=TOP_K,
        )

        print_results(
            query,
            results,
        )


if __name__ == "__main__":
    main()