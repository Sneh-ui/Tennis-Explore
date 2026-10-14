
import os
import sys
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent
BACKEND_DIR = DOCUMENTS_V2_DIR.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import EMBEDDING_MODEL_NAME

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

TOP_K = 15


def get_connection():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
        connect_timeout=30,
    )


def pgvector_search(query, embedding_model, top_k=TOP_K):
    query_embedding = embedding_model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")[0]

    vector_text = "[" + ",".join(
        str(float(value))
        for value in query_embedding
    ) + "]"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    dc.chunk_db_id,
                    dc.source_chunk_id,
                    d.file_name,
                    d.file_type,
                    dc.page_number,
                    dc.slide_number,
                    dc.chunk_text,
                    1 - (
                        ce.embedding <=> %s::extensions.vector
                    ) AS similarity
                FROM unstructured.chunk_embeddings ce
                JOIN unstructured.document_chunks dc
                    ON dc.chunk_db_id = ce.chunk_db_id
                JOIN unstructured.documents d
                    ON d.document_id = dc.document_id
                ORDER BY
                    ce.embedding <=> %s::extensions.vector
                LIMIT %s
                """,
                (vector_text, vector_text, top_k),
            )

            rows = cur.fetchall()

    candidates = []

    for row in rows:
        (
            chunk_db_id,
            chunk_id,
            source_file,
            file_type,
            page_number,
            slide_number,
            chunk_text,
            similarity,
        ) = row

        candidates.append({
            "chunk_db_id": chunk_db_id,
            "chunk_id": chunk_id,
            "source_file": source_file,
            "file_type": file_type,
            "page_number": page_number,
            "slide_number": slide_number,
            "text": chunk_text,
            "semantic_score": float(similarity),
        })

    return candidates


def main():
    print("=" * 65)
    print("TENNIS EXPLORE - SUPABASE PGVECTOR SEARCH")
    print("=" * 65)

    print("Loading embedding model...")
    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    while True:
        query = input(
            "\nEnter a question (or 'exit'): "
        ).strip()

        if query.lower() in {"exit", "quit", "q"}:
            break

        if not query:
            continue

        results = pgvector_search(
            query,
            embedding_model,
            top_k=TOP_K,
        )

        print("\nTOP PGVECTOR RESULTS")

        for rank, item in enumerate(results, start=1):
            print(
                f"{rank}. "
                f"Score={item['semantic_score']:.4f} | "
                f"{item['source_file']} | "
                f"{item['chunk_id']}"
            )


if __name__ == "__main__":
    main()
