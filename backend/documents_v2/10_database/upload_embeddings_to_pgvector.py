
import json
import os
import time
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv

# backend/documents_v2/10_database/upload_embeddings_to_pgvector.py
BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BACKEND_DIR / ".env")

EMBEDDINGS_DIR = (
    BACKEND_DIR / "documents_v2" / "outputs" / "embeddings"
)

BATCH_SIZE = 500

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    embeddings = np.load(
        EMBEDDINGS_DIR / "production_chunk_embeddings.npy",
        mmap_mode="r",
    )

    with (
        EMBEDDINGS_DIR / "production_chunk_metadata.json"
    ).open(encoding="utf-8") as file:
        metadata = json.load(file)

    if embeddings.ndim != 2 or embeddings.shape[1] != 384:
        raise ValueError("Expected 384-dimensional embeddings")

    if len(metadata) != embeddings.shape[0]:
        raise ValueError("Embedding and metadata counts differ")

    chunk_ids = [
        int(item["chunk_db_id"])
        for item in metadata
    ]

    if len(set(chunk_ids)) != len(chunk_ids):
        raise ValueError("Duplicate chunk IDs in metadata")

    print("=" * 60)
    print("TENNIS EXPLORE - PGVECTOR EMBEDDING UPLOAD")
    print("=" * 60)
    print("Total local embeddings:", len(metadata))
    print("Embedding dimensions  :", embeddings.shape[1])
    print("Batch size            :", BATCH_SIZE)

    start_time = time.time()

    with psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
        connect_timeout=30,
    ) as conn:

        with conn.cursor() as cur:
            cur.execute("""
                SELECT chunk_db_id, source_chunk_id
                FROM unstructured.document_chunks
                ORDER BY chunk_db_id
            """)
            db_rows = cur.fetchall()

        db_mapping = {
            int(chunk_id): source_chunk_id
            for chunk_id, source_chunk_id in db_rows
        }

        # Validate identities again before any writes.
        if len(db_mapping) != len(metadata):
            raise ValueError(
                "Database chunk count differs from local metadata"
            )

        for item in metadata:
            chunk_id = int(item["chunk_db_id"])

            if db_mapping.get(chunk_id) != item["chunk_id"]:
                raise ValueError(
                    f"Chunk identity mismatch: {chunk_id}"
                )

        print("Chunk identity validation: PASSED")

        with conn.cursor() as cur:
            cur.execute("""
                SELECT chunk_db_id
                FROM unstructured.chunk_embeddings
            """)
            existing_ids = {
                int(row[0]) for row in cur.fetchall()
            }

        print("Already stored:", len(existing_ids))

        pending_indices = [
            i for i, chunk_id in enumerate(chunk_ids)
            if chunk_id not in existing_ids
        ]

        print("Remaining to upload:", len(pending_indices))

        if not pending_indices:
            print("ALL EMBEDDINGS ALREADY UPLOADED")
            return

        uploaded = 0

        for start in range(0, len(pending_indices), BATCH_SIZE):
            batch_indices = pending_indices[
                start:start + BATCH_SIZE
            ]

            rows = []

            for i in batch_indices:
                vector = "[" + ",".join(
                    str(float(value))
                    for value in embeddings[i]
                ) + "]"

                rows.append((
                    chunk_ids[i],
                    vector,
                    MODEL_NAME,
                ))

            with conn.cursor() as cur:
                cur.executemany("""
                    INSERT INTO unstructured.chunk_embeddings
                        (chunk_db_id, embedding, model_name)
                    VALUES (
                        %s,
                        %s::extensions.vector,
                        %s
                    )
                    ON CONFLICT (chunk_db_id)
                    DO NOTHING
                """, rows)

            conn.commit()

            uploaded += len(rows)

            print(
                f"Submitted {uploaded:,} / "
                f"{len(pending_indices):,} remaining embeddings"
            )

        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM unstructured.chunk_embeddings
            """)
            final_count = cur.fetchone()[0]

        elapsed = time.time() - start_time

        print("=" * 60)
        print("UPLOAD COMPLETED")
        print("Total stored embeddings:", final_count)
        print("Expected embeddings    :", len(metadata))
        print("Elapsed seconds        :", round(elapsed, 2))

        if final_count != len(metadata):
            raise ValueError(
                "Final embedding count does not match"
            )

        print("FINAL COUNT VALIDATION PASSED")


if __name__ == "__main__":
    main()
