import json
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import (
    CHUNK_OUTPUT_DIR,
    EMBEDDING_OUTPUT_DIR,
    EMBEDDING_MODEL_NAME,
)


def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_json(data, path):
    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def load_all_chunks():
    all_chunks = []

    chunk_files = sorted(
        CHUNK_OUTPUT_DIR.glob("*_chunks.json")
    )

    print(
        f"Chunk files found: {len(chunk_files)}"
    )

    for chunk_file in chunk_files:
        data = load_json(chunk_file)

        for chunk in data.get("chunks", []):
            all_chunks.append(chunk)

    return all_chunks


def main():

    print()
    print("=" * 70)
    print("TENNIS EXPLORE - V2 EMBEDDINGS")
    print("=" * 70)

    chunks = load_all_chunks()

    if not chunks:
        print("No chunks found.")
        return

    print()
    print(
        f"Total chunks loaded: {len(chunks)}"
    )

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    print()
    print(
        f"Loading embedding model: "
        f"{EMBEDDING_MODEL_NAME}"
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    print()
    print("Generating embeddings...")

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    print()
    print(
        f"Embedding shape: "
        f"{embeddings.shape}"
    )

    embeddings_path = (
        EMBEDDING_OUTPUT_DIR
        / "chunk_embeddings.npy"
    )

    np.save(
        embeddings_path,
        embeddings.astype("float32"),
    )

    metadata = []

    for index, chunk in enumerate(chunks):

        metadata.append(
            {
                "vector_id": index,
                "chunk_id":
                    chunk["chunk_id"],
                "source_file":
                    chunk["source_file"],
                "file_type":
                    chunk["file_type"],
                "page_number":
                    chunk.get("page_number"),
                "slide_number":
                    chunk.get("slide_number"),
                "word_count":
                    chunk["word_count"],
                "text":
                    chunk["text"],
            }
        )

    metadata_path = (
        EMBEDDING_OUTPUT_DIR
        / "chunk_metadata.json"
    )

    save_json(
        metadata,
        metadata_path,
    )

    print()
    print("=" * 70)
    print("EMBEDDING SUMMARY")
    print("=" * 70)
    print(
        f"Chunks embedded     : "
        f"{len(chunks)}"
    )
    print(
        f"Vector dimensions   : "
        f"{embeddings.shape[1]}"
    )
    print(
        f"Embeddings saved to : "
        f"{embeddings_path}"
    )
    print(
        f"Metadata saved to   : "
        f"{metadata_path}"
    )


if __name__ == "__main__":
    main()