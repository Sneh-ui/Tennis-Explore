import os
import time

import faiss
import numpy as np
import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


load_dotenv()


def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "tennis_rankings"),
        "user": os.getenv("DB_USER", os.getenv("USER", "")),
        "password": os.getenv("DB_PASSWORD") or None,
    }


SAMPLE_SIZE = 100
QUERY = "How can a tennis player improve their serve?"


def main():
    print("=" * 70)
    print("TENNIS EXPLORE - FAISS REAL DATA BENCHMARK")
    print("=" * 70)

    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    config = get_db_config()

    # -------------------------------------------------------
    # Read exactly the same 100 real chunks
    # -------------------------------------------------------

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT chunk_db_id, chunk_text
                FROM unstructured.document_chunks
                WHERE chunk_text IS NOT NULL
                  AND BTRIM(chunk_text) <> ''
                ORDER BY chunk_db_id
                LIMIT %s;
            """, (SAMPLE_SIZE,))

            rows = cur.fetchall()

    print(f"\nReal chunks selected : {len(rows)}")

    texts = [row[1] for row in rows]

    # -------------------------------------------------------
    # Generate embeddings
    # -------------------------------------------------------

    start = time.perf_counter()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype="float32",
    )

    embedding_time = time.perf_counter() - start

    print(
        f"Embedding generation : "
        f"{embedding_time:.3f} seconds"
    )

    # -------------------------------------------------------
    # Build FAISS index
    # -------------------------------------------------------

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)

    start = time.perf_counter()

    index.add(embeddings)

    index_build_time = time.perf_counter() - start

    # -------------------------------------------------------
    # Generate query embedding
    # -------------------------------------------------------

    query_embedding = model.encode(
        [QUERY],
        normalize_embeddings=True,
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype="float32",
    )

    # -------------------------------------------------------
    # FAISS search
    # -------------------------------------------------------

    start = time.perf_counter()

    scores, indices = index.search(
        query_embedding,
        5,
    )

    search_time = time.perf_counter() - start

    print("\nQUERY:")
    print(QUERY)

    print("\nTOP 5 FAISS RESULTS")

    for rank, (idx, score) in enumerate(
        zip(indices[0], scores[0]),
        start=1,
    ):
        chunk_db_id, text = rows[idx]

        print("\n" + "-" * 70)
        print(f"Rank       : {rank}")
        print(f"Chunk ID   : {chunk_db_id}")
        print(f"Similarity : {float(score):.4f}")
        print(f"Text       : {text[:500]}")

    print("\n" + "=" * 70)
    print(
        f"FAISS index build time : "
        f"{index_build_time:.6f} seconds"
    )
    print(
        f"FAISS search time      : "
        f"{search_time:.6f} seconds"
    )
    print("=" * 70)

    print(
        "\nREAD-ONLY TEST - "
        "production database was not modified."
    )


if __name__ == "__main__":
    main()