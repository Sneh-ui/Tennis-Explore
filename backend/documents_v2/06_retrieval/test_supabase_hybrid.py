
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Locate backend/.env automatically
BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BACKEND_DIR / ".env")

question = "How can a tennis player improve their serve?"

print("Loading embedding model...")

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

embedding = model.encode(
    question,
    normalize_embeddings=True
)

vector_text = "[" + ",".join(
    str(float(x)) for x in embedding
) + "]"

sql = """
WITH semantic_results AS MATERIALIZED (
    SELECT
        chunk_db_id,
        ROW_NUMBER() OVER (
            ORDER BY distance ASC, chunk_db_id
        ) AS semantic_rank
    FROM (
        SELECT
            chunk_db_id,
            embedding <=> %s::extensions.vector AS distance
        FROM unstructured.chunk_embeddings
        ORDER BY embedding <=> %s::extensions.vector
        LIMIT 50
    ) s
),
keyword_results AS MATERIALIZED (
    SELECT
        chunk_db_id,
        ROW_NUMBER() OVER (
            ORDER BY keyword_score DESC, chunk_db_id
        ) AS keyword_rank
    FROM (
        SELECT
            chunk_db_id,
            ts_rank_cd(
                to_tsvector('english', chunk_text),
                websearch_to_tsquery('english', %s)
            ) AS keyword_score
        FROM unstructured.document_chunks
        WHERE to_tsvector('english', chunk_text)
              @@ websearch_to_tsquery('english', %s)
        ORDER BY keyword_score DESC, chunk_db_id
        LIMIT 50
    ) k
),
combined AS (
    SELECT
        COALESCE(s.chunk_db_id, k.chunk_db_id) AS chunk_db_id,
        s.semantic_rank,
        k.keyword_rank,
        (
            COALESCE(0.70 / (60 + s.semantic_rank), 0)
            +
            COALESCE(0.30 / (60 + k.keyword_rank), 0)
        ) AS hybrid_score
    FROM semantic_results s
    FULL OUTER JOIN keyword_results k
        ON s.chunk_db_id = k.chunk_db_id
)
SELECT
    d.file_name,
    c.semantic_rank,
    c.keyword_rank,
    ROUND(c.hybrid_score::numeric, 6)
FROM combined c
JOIN unstructured.document_chunks dc
    ON dc.chunk_db_id = c.chunk_db_id
JOIN unstructured.documents d
    ON d.document_id = dc.document_id
ORDER BY c.hybrid_score DESC, c.chunk_db_id
LIMIT 15;
"""

print("Connecting to Supabase...")

with psycopg.connect(
    host=os.environ["DB_HOST"],
    port=os.environ.get("DB_PORT", "5432"),
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    sslmode="require",
) as conn:
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (vector_text, vector_text, question, question)
        )
        results = cur.fetchall()

print("\nQUESTION:", question)
print("\nTOP 15 HYBRID RESULTS\n")

for rank, row in enumerate(results, 1):
    filename, semantic_rank, keyword_rank, score = row

    print(
        f"{rank:2d}. "
        f"Hybrid={score} | "
        f"SemanticRank={semantic_rank} | "
        f"KeywordRank={keyword_rank} | "
        f"{filename}"
    )

print("\nHybrid retrieval test completed.")
