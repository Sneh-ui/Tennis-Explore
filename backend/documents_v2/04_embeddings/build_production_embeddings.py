import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------
# PROJECT CONFIG
# ---------------------------------------------------------

CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import (
    EMBEDDING_OUTPUT_DIR,
    EMBEDDING_MODEL_NAME,
)


load_dotenv()


# ---------------------------------------------------------
# DATABASE CONFIG
# ---------------------------------------------------------

def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "tennis_rankings"),
        "user": os.getenv("DB_USER", os.getenv("USER", "")),
        "password": os.getenv("DB_PASSWORD") or None,
    }


# ---------------------------------------------------------
# DATABASE CHUNK LOADING
# ---------------------------------------------------------

def load_chunks(limit=None):

    query = """
        SELECT
            c.chunk_db_id,
            c.source_chunk_id,
            d.file_name,
            d.file_type,
            c.page_number,
            c.slide_number,
            c.word_count,
            c.chunk_text
        FROM unstructured.document_chunks AS c
        JOIN unstructured.documents AS d
            ON d.document_id = c.document_id
        WHERE c.chunk_text IS NOT NULL
          AND BTRIM(c.chunk_text) <> ''
        ORDER BY c.chunk_db_id
    """

    params = ()

    if limit is not None:
        query += " LIMIT %s"
        params = (limit,)

    config = get_db_config()

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    chunks = []

    for row in rows:
        chunks.append(
            {
                "chunk_db_id": row[0],
                "chunk_id": row[1],
                "source_file": row[2],
                "file_type": row[3],
                "page_number": row[4],
                "slide_number": row[5],
                "word_count": row[6],
                "text": row[7],
            }
        )

    return chunks


# ---------------------------------------------------------
# JSON HELPER
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Build production embeddings from "
            "Supabase PostgreSQL chunks."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Optional number of chunks to embed. "
            "Use this for testing before a full run."
        ),
    )

    args = parser.parse_args()

    print()
    print("=" * 70)
    print(
        "TENNIS EXPLORE - "
        "PRODUCTION EMBEDDINGS"
    )
    print("=" * 70)

    print()
    print(
        "Loading chunks from shared PostgreSQL..."
    )

    chunks = load_chunks(
        limit=args.limit
    )

    if not chunks:
        print("No chunks found.")
        return

    print(
        f"Chunks loaded: {len(chunks)}"
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

    embeddings = embeddings.astype(
        "float32"
    )

    print()
    print(
        f"Embedding shape: "
        f"{embeddings.shape}"
    )

    # -----------------------------------------------------
    # USE SEPARATE PRODUCTION OUTPUTS
    # -----------------------------------------------------

    if args.limit is None:
        embeddings_name = (
            "production_chunk_embeddings.npy"
        )
        metadata_name = (
            "production_chunk_metadata.json"
        )
    else:
        embeddings_name = (
            "production_test_chunk_embeddings.npy"
        )
        metadata_name = (
            "production_test_chunk_metadata.json"
        )

    embeddings_path = (
        EMBEDDING_OUTPUT_DIR
        / embeddings_name
    )

    metadata_path = (
        EMBEDDING_OUTPUT_DIR
        / metadata_name
    )

    # -----------------------------------------------------
    # SAVE EMBEDDINGS
    # -----------------------------------------------------

    np.save(
        embeddings_path,
        embeddings,
    )

    # -----------------------------------------------------
    # BUILD VECTOR METADATA
    # -----------------------------------------------------

    metadata = []

    for vector_id, chunk in enumerate(
        chunks
    ):
        metadata.append(
            {
                "vector_id": vector_id,
                "chunk_db_id":
                    chunk["chunk_db_id"],
                "chunk_id":
                    chunk["chunk_id"],
                "source_file":
                    chunk["source_file"],
                "file_type":
                    chunk["file_type"],
                "page_number":
                    chunk["page_number"],
                "slide_number":
                    chunk["slide_number"],
                "word_count":
                    chunk["word_count"],
                "text":
                    chunk["text"],
            }
        )

    save_json(
        metadata,
        metadata_path,
    )

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if len(metadata) != len(embeddings):
        raise ValueError(
            "Metadata and embedding counts "
            "do not match."
        )

    print()
    print("=" * 70)
    print("PRODUCTION EMBEDDING SUMMARY")
    print("=" * 70)

    print(
        f"Chunks embedded       : "
        f"{len(chunks)}"
    )

    print(
        f"Vector dimensions     : "
        f"{embeddings.shape[1]}"
    )

    print(
        f"First chunk_db_id     : "
        f"{metadata[0]['chunk_db_id']}"
    )

    print(
        f"Last chunk_db_id      : "
        f"{metadata[-1]['chunk_db_id']}"
    )

    print(
        f"Embeddings saved to   : "
        f"{embeddings_path}"
    )

    print(
        f"Metadata saved to     : "
        f"{metadata_path}"
    )

    print()
    print(
        "Existing sample embedding files "
        "were NOT overwritten."
    )


if __name__ == "__main__":
    main()