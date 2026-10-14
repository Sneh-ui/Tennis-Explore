from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.structured_data.queries import (
    search_players,
    get_player_ranking_history,
    get_latest_player_rankings,
)
import re
from backend.unstructured_chat.router import unstructured_chat, ChatRequest
from backend.unstructured_chat.router import router as unstructured_router
from backend.structured_data.structured_chat import answer_structured_question
from backend.auth.router import router as auth_router
from backend.auth.deps import get_current_user_db
from backend.structured_data.chat_history import (
    save_chat_history,
    get_chat_history,
)
from pydantic import BaseModel

app = FastAPI(
    title="Tennis EXPLORE Structured Data API",
    version="1.0.0",
)

# CORS for frontend (Vite dev: http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(unstructured_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/players/search")
def player_search(name: str):
    players = search_players(name)
    return {
        "query": name,
        "count": len(players),
        "players": players,
    }


@app.get("/players/{player_id}/rankings")
def player_ranking_history(player_id: int):
    rankings = get_player_ranking_history(player_id)

    if not rankings:
        raise HTTPException(
            status_code=404,
            detail="No ranking history found for this player.",
        )

    return {
        "player_id": player_id,
        "count": len(rankings),
        "rankings": rankings,
    }


@app.get("/players/{player_id}/rankings/latest")
def latest_player_rankings(player_id: int):
    rankings = get_latest_player_rankings(player_id)

    if not rankings:
        raise HTTPException(
            status_code=404,
            detail="No ranking data found for this player.",
        )

    return {
        "player_id": player_id,
        "rankings": rankings,
    }
@app.post("/structured/chat")
def structured_chat(question: str):
    result = answer_structured_question(question)
    return result


class AutoChatRequest(BaseModel):
    question: str


def detect_chat_route(question: str):
    q = question.lower().strip()

    # Questions about recorded tennis data
    structured_patterns = [
        r"\brankings?\b",
        r"\branked\b",
        r"\batp\b",
        r"\bwta\b",
        r"\bitf\b",
        r"\bstatistics?\b",
        r"\bstats\b",
        r"\bmatch results?\b",
        r"\bmatch scores?\b",
        r"\bwin percentage\b",
        r"\bwin rate\b",
        r"\bhead.to.head\b",
        r"\bleaderboard\b",
        r"\btop \d+ players?\b",
        r"\bplayer records?\b",
    ]

    # Questions about coaching, training and research
    unstructured_patterns = [
        r"\bhow (can|do|should|to)\b",
        r"\bimprov(e|ing|ement)\b",
        r"\btrain(ing)?\b",
        r"\bpractice\b",
        r"\btechniques?\b",
        r"\bmental\b",
        r"\bpsycholog(y|ical)\b",
        r"\banxiety\b",
        r"\bconfidence\b",
        r"\bmotivation\b",
        r"\bmindfulness\b",
        r"\bbenefits?\b",
        r"\bexercises?\b",
        r"\binjury prevention\b",
        r"\bcoaching\b",
        r"\bresearch\b",
        r"\bstrateg(y|ies)\b",
    ]

    structured = any(
        re.search(pattern, q) for pattern in structured_patterns
    )

    unstructured = any(
        re.search(pattern, q) for pattern in unstructured_patterns
    )

    if structured and not unstructured:
        return "structured"

    if unstructured and not structured:
        return "unstructured"

    # Mixed or unclear questions should not be guessed.
    return "clarification"


@app.post("/chat/auto")
def automatic_chat(payload: AutoChatRequest):
    question = payload.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    route = detect_chat_route(question)

    if route == "structured":
        result = structured_chat(question)

    elif route == "unstructured":
        result = unstructured_chat(
            ChatRequest(question=question)
        )

    else:
        return {
            "status": "clarification",
            "route": "clarification",
            "answer": (
                "Are you asking about player rankings and "
                "match statistics, or tennis training and "
                "research advice? Please provide a little "
                "more detail."
            ),
            "sources": [],
        }

    if not isinstance(result, dict):
        raise HTTPException(
            status_code=502,
            detail="Unexpected chatbot response."
        )

    return {
        **result,
        "route": route,
        "sources": result.get("sources") or [],
    }


class ChatHistoryRequest(BaseModel):
    question: str
    answer: str


@app.post("/chat/history")
def create_chat_history(
    payload: ChatHistoryRequest,
    current_user: dict = Depends(get_current_user_db),
):
    return save_chat_history(
        current_user["id"],
        payload.question,
        payload.answer,
    )


@app.get("/chat/history")
def chat_history(
    current_user: dict = Depends(get_current_user_db),
):
    return {
        "history": get_chat_history(current_user["id"])
    }
