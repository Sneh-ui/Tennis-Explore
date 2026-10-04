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


SAMPLE_SIZE = 5000

QUERIES = [
    "How can a tennis player improve their serve?",
    "What causes tennis elbow?",
    "How does fatigue affect tennis performance?",
]


def vector_to_string(vector):
    return "[" + ",".join(map(str, vector.tolist())) + "]"


def main():
    print("=" * 75)
    print("TENNIS EXPLORE - FAISS VS PGVECTOR BENCHMARK")
    print("=" * 75)

    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    config = get_db_config()

    # -------------------------------------------------------
    # LOAD REAL CHUNKS
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
    # GENERATE EMBEDDINGS ONCE
    # -------------------------------------------------------

    print("\nGenerating shared embeddings...")

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

    print(
        f"Embedding shape      : "
        f"{embeddings.shape}"
    )

    # -------------------------------------------------------
    # BUILD FAISS INDEX
    # -------------------------------------------------------

    dimension = embeddings.shape[1]

    faiss_index = faiss.IndexFlatIP(
        dimension
    )

    start = time.perf_counter()

    faiss_index.add(
        embeddings
    )

    faiss_build_time = (
        time.perf_counter() - start
    )

    print(
        f"FAISS index build    : "
        f"{faiss_build_time:.6f} seconds"
    )

    # -------------------------------------------------------
    # PGVECTOR TEMP TABLE
    # -------------------------------------------------------

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TEMP TABLE pgvector_benchmark (
                    chunk_db_id BIGINT PRIMARY KEY,
                    chunk_text TEXT NOT NULL,
                    embedding vector(384)
                );
            """)

            print("\nLoading vectors into temporary pgvector table...")

            start = time.perf_counter()

            for (
                (chunk_db_id, chunk_text),
                embedding,
            ) in zip(rows, embeddings):

                cur.execute("""
                    INSERT INTO pgvector_benchmark (
                        chunk_db_id,
                        chunk_text,
                        embedding
                    )
                    VALUES (%s, %s, %s::vector);
                """, (
                    chunk_db_id,
                    chunk_text,
                    vector_to_string(embedding),
                ))

            pgvector_load_time = (
                time.perf_counter() - start
            )

            print(
                f"pgvector load time   : "
                f"{pgvector_load_time:.3f} seconds"
            )

            # ------------------------------------------------
            # RUN SAME QUERIES THROUGH BOTH SYSTEMS
            # ------------------------------------------------

            for query in QUERIES:

                print("\n" + "=" * 75)
                print(f"QUERY: {query}")
                print("=" * 75)

                query_embedding = model.encode(
                    [query],
                    normalize_embeddings=True,
                )

                query_embedding = np.asarray(
                    query_embedding,
                    dtype="float32",
                )

                # --------------------------------------------
                # FAISS
                # --------------------------------------------

                start = time.perf_counter()

                faiss_scores, faiss_indices = (
                    faiss_index.search(
                        query_embedding,
                        5,
                    )
                )

                faiss_search_time = (
                    time.perf_counter() - start
                )

                faiss_ids = [
                    rows[index][0]
                    for index
                    in faiss_indices[0]
                ]

                # --------------------------------------------
                # PGVECTOR
                # --------------------------------------------

                query_vector = vector_to_string(
                    query_embedding[0]
                )

                start = time.perf_counter()

                cur.execute("""
                    SELECT
                        chunk_db_id,
                        1 - (
                            embedding <=> %s::vector
                        ) AS similarity
                    FROM pgvector_benchmark
                    ORDER BY
                        embedding <=> %s::vector
                    LIMIT 5;
                """, (
                    query_vector,
                    query_vector,
                ))

                pg_results = cur.fetchall()

                pgvector_search_time = (
                    time.perf_counter() - start
                )

                pgvector_ids = [
                    row[0]
                    for row in pg_results
                ]

                # --------------------------------------------
                # COMPARE
                # --------------------------------------------

                print("\nFAISS Top 5:")
                print(faiss_ids)

                print("pgvector Top 5:")
                print(pgvector_ids)

                exact_match = (
                    faiss_ids
                    == pgvector_ids
                )

                overlap = len(
                    set(faiss_ids)
                    & set(pgvector_ids)
                )

                print(
                    f"\nExact ranking match : "
                    f"{exact_match}"
                )

                print(
                    f"Top-5 overlap        : "
                    f"{overlap}/5"
                )

                print(
                    f"FAISS search time    : "
                    f"{faiss_search_time:.6f} sec"
                )

                print(
                    f"pgvector search time : "
                    f"{pgvector_search_time:.6f} sec"
                )

            print("\n" + "=" * 75)
            print("BENCHMARK COMPLETE")
            print("=" * 75)

            print(
                f"Chunks tested        : "
                f"{len(rows)}"
            )

            print(
                f"Embedding dimension  : "
                f"{dimension}"
            )

            print(
                "\nTemporary pgvector table only."
            )

            print(
                "Production document_chunks "
                "table was NOT modified."
            )


if __name__ == "__main__":
    main()