import json
import sys
from pathlib import Path

import faiss
import numpy as np


CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import (
    EMBEDDING_OUTPUT_DIR,
    FAISS_OUTPUT_DIR,
)


def load_metadata(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def main():

    print()
    print("=" * 70)
    print("TENNIS EXPLORE - PRODUCTION FAISS INDEX")
    print("=" * 70)

    embeddings_path = (
        EMBEDDING_OUTPUT_DIR
        / "production_chunk_embeddings.npy"
    )

    metadata_path = (
        EMBEDDING_OUTPUT_DIR
        / "production_chunk_metadata.json"
    )

    if not embeddings_path.exists():
        raise FileNotFoundError(
            f"Production embeddings not found: {embeddings_path}"
        )

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Production metadata not found: {metadata_path}"
        )

    embeddings = np.load(
        embeddings_path
    ).astype("float32")

    metadata = load_metadata(
        metadata_path
    )

    print()
    print(
        f"Embeddings loaded : "
        f"{embeddings.shape}"
    )

    print(
        f"Metadata records  : "
        f"{len(metadata)}"
    )

    if len(embeddings) != len(metadata):
        raise ValueError(
            "Production embedding and metadata "
            "counts do not match."
        )

    if embeddings.ndim != 2:
        raise ValueError(
            "Embeddings must be a 2D array."
        )

    if embeddings.shape[1] != 384:
        raise ValueError(
            f"Expected 384 dimensions, "
            f"found {embeddings.shape[1]}."
        )

    # Verify vector_id alignment before indexing.
    for expected_id, item in enumerate(metadata):
        if item["vector_id"] != expected_id:
            raise ValueError(
                f"Metadata alignment error at "
                f"vector_id {expected_id}."
            )

    dimension = embeddings.shape[1]

    # Embeddings were already normalized when generated.
    # Inner product therefore acts as cosine similarity.
    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(
        embeddings
    )

    if index.ntotal != len(metadata):
        raise ValueError(
            "FAISS vector count does not match "
            "production metadata count."
        )

    faiss_path = (
        FAISS_OUTPUT_DIR
        / "production_documents_v2.index"
    )

    faiss.write_index(
        index,
        str(faiss_path),
    )

    print()
    print("=" * 70)
    print("PRODUCTION FAISS SUMMARY")
    print("=" * 70)

    print(
        f"Vector dimension : "
        f"{dimension}"
    )

    print(
        f"Vectors indexed  : "
        f"{index.ntotal}"
    )

    print(
        "Index type       : IndexFlatIP"
    )

    print(
        f"Index saved to   : "
        f"{faiss_path}"
    )

    print()
    print(
        "Existing sample FAISS index "
        "was NOT overwritten."
    )


if __name__ == "__main__":
    main()