"""
video_supabase_search.py
------------------------
Sumukha's video transcript retrieval from Supabase.

Mirrors production_supabase_rerank.py exactly — same hybrid search
pattern (semantic + keyword via RRF), same candidate/rerank structure,
same return dict shape — but queries the video schema instead of
the unstructured schema. Does NOT touch the group's tables.
"""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

CURRENT_FILE  = Path(__file__).resolve()
DOCUMENTS_DIR = CURRENT_FILE.parent.parent
BACKEND_DIR   = DOCUMENTS_DIR.parent

sys.path.insert(0, str(DOCUMENTS_DIR))

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

CANDIDATE_K = 20   # video candidates before reranking

# ── Hybrid SQL — mirrors the group's RRF pattern exactly ─────────────────────
# Queries video.chunk_embeddings + video.video_chunks + video.video_files
# instead of unstructured.*

VIDEO_SQL = """
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
        FROM video.chunk_embeddings
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
        FROM video.video_chunks
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
    vc.chunk_db_id,
    vc.source_chunk_id,
    vf.file_name        AS source_file,
    vf.file_type,
    vf.display_title,
    vf.main_topic,
    vc.chunk_text,
    c.semantic_rank,
    c.keyword_rank,
    c.hybrid_score
FROM combined c
JOIN video.video_chunks vc
    ON vc.chunk_db_id = c.chunk_db_id
JOIN video.video_files vf
    ON vf.video_id = vc.video_id
ORDER BY c.hybrid_score DESC, vc.chunk_db_id
LIMIT %s
"""


def _get_connection():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
        connect_timeout=30,
    )


def get_video_candidates(question: str, model) -> list[dict]:
    """
    Hybrid search over video transcripts in Supabase.
    Returns candidates in the same dict shape as the group's get_candidates().
    """
    embedding = model.encode(question, normalize_embeddings=True)
    vec_str   = "[" + ",".join(str(float(x)) for x in embedding) + "]"

    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                VIDEO_SQL,
                (vec_str, vec_str, question, question, CANDIDATE_K),
            )
            rows = cur.fetchall()

    candidates = []
    for row in rows:
        (
            chunk_db_id,
            source_chunk_id,
            source_file,
            file_type,
            display_title,
            main_topic,
            text,
            semantic_rank,
            keyword_rank,
            hybrid_score,
        ) = row

        candidates.append({
            "chunk_db_id":   chunk_db_id,
            "chunk_id":      source_chunk_id,
            "source_file":   display_title or source_file,
            "file_type":     "video",          # always tag as video
            "page_number":   None,
            "slide_number":  None,
            "text":          text,
            "semantic_rank": semantic_rank,
            "keyword_rank":  keyword_rank,
            "hybrid_score":  float(hybrid_score),
        })

    return candidates
