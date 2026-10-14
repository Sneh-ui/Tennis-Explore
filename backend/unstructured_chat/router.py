
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


@router.post("/chat")
def unstructured_chat(payload: ChatRequest):
    try:
        with rag_lock:
            rag, embedding_model, reranker = load_pipeline()

            candidates = rag.retrieval.get_candidates(
                payload.question, embedding_model
            )

            if not candidates:
                return {"status": "no_evidence", "answer": rag.REFUSAL}

            ranked = rag.retrieval.rerank(
                payload.question, candidates, reranker
            )

            evidence = rag.get_focused_evidence(
                payload.question, ranked
            )

            if not evidence:
                return {"status": "no_evidence", "answer": rag.REFUSAL}

            
        answer = rag.generate_answer(payload.question, evidence)

        sources = []
        seen_sources = set()

        for item in evidence:
            file_name = item.get("source_file")
            file_type = item.get("file_type")
            page_number = item.get("page_number")
            slide_number = item.get("slide_number")

            source_key = (file_name, page_number, slide_number)

            if source_key in seen_sources:
                continue

            seen_sources.add(source_key)

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
        }


    except Exception:
        logger.exception("Unstructured chatbot failed")
        raise HTTPException(
            status_code=503,
            detail="Unstructured chatbot unavailable. Check Supabase and Ollama.",
        )

