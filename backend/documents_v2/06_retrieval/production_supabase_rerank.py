
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, CrossEncoder

CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_DIR = CURRENT_FILE.parent.parent
BACKEND_DIR = DOCUMENTS_DIR.parent

sys.path.insert(0, str(DOCUMENTS_DIR))

from config import EMBEDDING_MODEL_NAME, RERANKER_MODEL_NAME

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

CANDIDATE_K = 50
FINAL_TOP_K = 5

SQL = """
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
    dc.chunk_db_id,
    dc.source_chunk_id,
    d.file_name,
    d.file_type,
    dc.page_number,
    dc.slide_number,
    dc.chunk_text,
    c.semantic_rank,
    c.keyword_rank,
    c.hybrid_score
FROM combined c
JOIN unstructured.document_chunks dc
    ON dc.chunk_db_id = c.chunk_db_id
JOIN unstructured.documents d
    ON d.document_id = dc.document_id
ORDER BY c.hybrid_score DESC, c.chunk_db_id
LIMIT %s
"""


def get_candidates(question, model):
    embedding = model.encode(
        question,
        normalize_embeddings=True
    )

    vector_text = "[" + ",".join(
        str(float(x)) for x in embedding
    ) + "]"

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
            cur.execute(
                SQL,
                (
                    vector_text,
                    vector_text,
                    question,
                    question,
                    CANDIDATE_K,
                )
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
            text,
            semantic_rank,
            keyword_rank,
            hybrid_score,
        ) = row

        candidates.append({
            "chunk_db_id": chunk_db_id,
            "chunk_id": chunk_id,
            "source_file": source_file,
            "file_type": file_type,
            "page_number": page_number,
            "slide_number": slide_number,
            "text": text,
            "semantic_rank": semantic_rank,
            "keyword_rank": keyword_rank,
            "hybrid_score": float(hybrid_score),
        })

    return candidates


def rerank(question, candidates, reranker):
    if not candidates:
        return []

    pairs = [
        [question, item["text"]]
        for item in candidates
    ]

    scores = reranker.predict(pairs)

    for item, score in zip(candidates, scores):
        item["reranker_score"] = float(score)

    return sorted(
        candidates,
        key=lambda item: item["reranker_score"],
        reverse=True,
    )[:FINAL_TOP_K]


def main():
    print("Loading embedding model...")
    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    print("Loading reranker...")
    reranker_model = CrossEncoder(
        RERANKER_MODEL_NAME
    )

    while True:
        question = input(
            "\nEnter question (or exit): "
        ).strip()

        if question.lower() in {"exit", "quit", "q"}:
            break

        if not question:
            continue

        candidates = get_candidates(
            question,
            embedding_model
        )

        print(
            f"\nRetrieved {len(candidates)} "
            "hybrid candidates."
        )

        results = rerank(
            question,
            candidates,
            reranker_model
        )

        print("\nTOP 5 AFTER RERANKING\n")

        for rank, item in enumerate(results, 1):
            print(f"\nRank: {rank}")
            print(f"Source: {item['source_file']}")
            print(f"Chunk: {item['chunk_id']}")
            print(f"Page: {item['page_number']}")
            print(f"Slide: {item['slide_number']}")
            print(
                f"Reranker score: "
                f"{item['reranker_score']:.4f}"
            )
            print(f"Text: {item['text'][:300]}")


if __name__ == "__main__":
    main()
