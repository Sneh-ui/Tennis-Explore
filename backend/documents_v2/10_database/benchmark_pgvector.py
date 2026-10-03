import os
import time

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
    print("TENNIS EXPLORE - PGVECTOR REAL DATA BENCHMARK")
    print("=" * 70)

    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    config = get_db_config()

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:

            # -----------------------------------------------
            # Create temporary benchmark table
            # -----------------------------------------------

            cur.execute("""
                CREATE TEMP TABLE pgvector_chunk_benchmark (
                    chunk_db_id BIGINT PRIMARY KEY,
                    chunk_text TEXT NOT NULL,
                    embedding vector(384)
                );
            """)

            # -----------------------------------------------
            # Read real Tennis Explore chunks
            # -----------------------------------------------

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

            # -----------------------------------------------
            # Generate embeddings
            # -----------------------------------------------

            start = time.perf_counter()

            embeddings = model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=True,
            )

            embedding_time = time.perf_counter() - start

            print(
                f"Embedding generation : "
                f"{embedding_time:.3f} seconds"
            )

            # -----------------------------------------------
            # Store sample embeddings in pgvector
            # -----------------------------------------------

            for (chunk_db_id, chunk_text), embedding in zip(
                rows,
                embeddings,
            ):
                cur.execute("""
                    INSERT INTO pgvector_chunk_benchmark (
                        chunk_db_id,
                        chunk_text,
                        embedding
                    )
                    VALUES (%s, %s, %s::vector);
                """, (
                    chunk_db_id,
                    chunk_text,
                    "[" + ",".join(
                        map(str, embedding.tolist())
                    ) + "]",
                ))

            # -----------------------------------------------
            # Embed real user query
            # -----------------------------------------------

            query_embedding = model.encode(
                [QUERY],
                normalize_embeddings=True,
            )[0]

            query_vector = (
                "["
                + ",".join(map(str, query_embedding.tolist()))
                + "]"
            )

            # -----------------------------------------------
            # pgvector cosine search
            # -----------------------------------------------

            start = time.perf_counter()

            cur.execute("""
                SELECT
                    chunk_db_id,
                    chunk_text,
                    1 - (embedding <=> %s::vector)
                        AS cosine_similarity
                FROM pgvector_chunk_benchmark
                ORDER BY embedding <=> %s::vector
                LIMIT 5;
            """, (
                query_vector,
                query_vector,
            ))

            results = cur.fetchall()

            search_time = time.perf_counter() - start

            print("\nQUERY:")
            print(QUERY)

            print("\nTOP 5 PGVECTOR RESULTS")

            for rank, row in enumerate(results, start=1):
                chunk_db_id, text, similarity = row

                print("\n" + "-" * 70)
                print(f"Rank       : {rank}")
                print(f"Chunk ID   : {chunk_db_id}")
                print(
                    f"Similarity : {float(similarity):.4f}"
                )
                print(f"Text       : {text[:500]}")

            print("\n" + "=" * 70)
            print(
                f"pgvector search time : "
                f"{search_time:.6f} seconds"
            )
            print("=" * 70)

            print(
                "\nTEMPORARY TEST ONLY - "
                "production tables were not modified."
            )


if __name__ == "__main__":
    main()