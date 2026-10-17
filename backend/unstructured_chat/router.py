
import importlib.util
import logging
import threading
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/unstructured", tags=["Unstructured Chatbot"])

GENERATOR_FILE = (
    Path(__file__).resolve().parents[1]
    / "documents_v2"
    / "08_generation"
    / "production_supabase_generate_answer.py"
)

VIDEO_SEARCH_FILE = (
    Path(__file__).resolve().parents[1]
    / "documents_v2"
    / "06_retrieval"
    / "video_supabase_search.py"
)

rag_lock = threading.Lock()


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@lru_cache(maxsize=1)
def load_pipeline():
    from sentence_transformers import SentenceTransformer, CrossEncoder

    spec = importlib.util.spec_from_file_location(
        "tennis_unstructured_rag", GENERATOR_FILE
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load RAG generator")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    embedding_model = SentenceTransformer(module.EMBEDDING_MODEL_NAME)
    reranker = CrossEncoder(module.RERANKER_MODEL_NAME)

    return module, embedding_model, reranker


def _get_video_candidates(question: str, embedding_model) -> list:
    try:
        spec = importlib.util.spec_from_file_location(
            "video_supabase_search", VIDEO_SEARCH_FILE
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        candidates = mod.get_video_candidates(question, embedding_model)
        for c in candidates:
            c.setdefault("page_number", None)
            c.setdefault("slide_number", None)
        return candidates or []
    except Exception as exc:
        logger.warning("Video Supabase search failed: %s", exc)
        return []


def _split_reranked(ranked: list):
    """Split reranked candidates into doc and video lists."""
    doc_items = [c for c in ranked if c.get("file_type") != "video"]
    video_items = [c for c in ranked if c.get("file_type") == "video"]
    return doc_items, video_items


@router.post("/chat")
def unstructured_chat(payload: ChatRequest):
    try:
        with rag_lock:
            rag, embedding_model, reranker = load_pipeline()

            doc_candidates = rag.retrieval.get_candidates(
                payload.question, embedding_model
            )

            video_candidates = _get_video_candidates(payload.question, embedding_model)
            candidates = doc_candidates + video_candidates

            logger.info(
                "Candidates: %d doc + %d video = %d total",
                len(doc_candidates), len(video_candidates), len(candidates)
            )

            if not candidates:
                return {
                    "status": "no_evidence",
                    "answer": rag.REFUSAL,
                    "video_sources_included": False,
                }

            # Rerank the full pool (doc + video) together
            ranked = rag.retrieval.rerank(
                payload.question, candidates, reranker
            )

            # Split: doc chunks go through get_focused_evidence (hits unstructured DB)
            # video chunks are used directly — they're not in unstructured.document_chunks
            doc_ranked, video_ranked = _split_reranked(ranked)

            doc_evidence = []
            if doc_ranked:
                doc_evidence = rag.get_focused_evidence(payload.question, doc_ranked)

            # Use top-3 video chunks directly as evidence
            video_evidence = video_ranked[:3]

            evidence = doc_evidence + video_evidence

            if not evidence:
                return {
                    "status": "no_evidence",
                    "answer": rag.REFUSAL,
                    "video_sources_included": False,
                }

        answer = rag.generate_answer(payload.question, evidence)

        sources = []
        seen_sources = set()
        video_sources_included = False

        for item in evidence:
            file_name = item.get("source_file")
            file_type = item.get("file_type")
            page_number = item.get("page_number")
            slide_number = item.get("slide_number")

            source_key = (file_name, page_number, slide_number)

            if source_key in seen_sources:
                continue

            seen_sources.add(source_key)

            if file_type == "video":
                video_sources_included = True

            sources.append({
                "file_name": file_name,
                "file_type": file_type,
                "page_number": page_number,
                "slide_number": slide_number,
            })

        return {
            "status": "answered" if answer else "no_answer",
            "answer": answer or "No answer generated.",
            "sources": sources if answer and answer != rag.REFUSAL else [],
            "video_sources_included": video_sources_included,
        }

    except Exception:
        logger.exception("Unstructured chatbot failed")
        raise HTTPException(
            status_code=503,
            detail="Unstructured chatbot unavailable. Check Supabase and Ollama.",
        )
