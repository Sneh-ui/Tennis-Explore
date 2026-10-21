from fastapi import FastAPI, HTTPException, Depends
import json
import re
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

from backend.structured_data.queries import (
    search_players,
    get_player_ranking_history,
    get_latest_player_rankings,
)
from backend.unstructured_chat.router import unstructured_chat, ChatRequest
from backend.unstructured_chat.router import router as unstructured_router
from backend.structured_data.structured_chat import (
    answer_structured_question,
    understand_question,
    merge_followup_context,
)
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
def structured_chat(question: str, context: str | None = None):
    current = understand_question(question)

    question_lower = question.lower()

    # Deterministic guard for explicit ranking-style requests such as
    # "Show me the top 10 WTA players". The language router can otherwise
    # confuse these with a generic player-list request.
    explicit_top_ranking = re.search(
        r"\\btop\\s+(\\d+)\\s+(atp|wta|itf|utr)\\b",
        question_lower,
        re.IGNORECASE,
    )

    if explicit_top_ranking:
        current["intent"] = "top_rankings"
        current["limit"] = int(explicit_top_ranking.group(1))
        current["source"] = explicit_top_ranking.group(2).upper()

        if not current.get("ranking_type"):
            current["ranking_type"] = "singles"

    # Correct month-only ranking questions.
    # Example: "Top 5 ATP in March" should mean March of the current year,
    # rather than accepting an invented/default year from the router.
    month_names = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    explicit_year = re.search(r"\\b(?:19|20)\\d{2}\\b", question)

    if not explicit_year:
        for month_name, month_number in month_names.items():
            if re.search(rf"\\b{month_name}\\b", question_lower):
                year = datetime.now().year

                if month_number == 12:
                    next_year = year + 1
                    next_month = 1
                else:
                    next_year = year
                    next_month = month_number + 1

                from datetime import date, timedelta

                current["start_date"] = date(
                    year, month_number, 1
                ).isoformat()

                current["end_date"] = (
                    date(next_year, next_month, 1) - timedelta(days=1)
                ).isoformat()
                break

    previous = None
    if context:
        try:
            previous = json.loads(context)
        except json.JSONDecodeError:
            previous = None

    # Only inherit context for clearly conversational follow-ups.
    # Conversational follow-up, including a short answer to a
    # clarification such as "ATP" after we asked for an organisation.
    normalized_question = " ".join(question.strip().lower().split())

    source_reply = bool(
        re.fullmatch(
            r"(atp|wta|itf|utr)(?:\s+(?:singles|doubles))?",
            normalized_question,
            re.IGNORECASE,
        )
    )

    is_followup = bool(
        previous
        and (
            source_reply
            or re.match(
                r"^\s*(what about|how about|and\b|what is his\b|what is her\b|his\b|her\b)",
                question,
                re.IGNORECASE,
            )
        )
    )

    if is_followup:
        resolved = merge_followup_context(current, previous)

        # Short follow-ups normally change one slot, not the user's intent.
        resolved["intent"] = previous.get("intent", resolved.get("intent"))

        question_lower = question.lower()

        # A new date replaces the old date period.
        if current.get("start_date") or current.get("end_date"):
            resolved["start_date"] = current.get("start_date")
            resolved["end_date"] = current.get("end_date")

        # Explicit source replaces the previous source.
        if current.get("source"):
            resolved["source"] = current.get("source")

        # Explicit player replaces the previous player.
        if current.get("player_name"):
            resolved["player_name"] = current.get("player_name")

        # Explicit ranking type replaces the previous type.
        if current.get("ranking_type"):
            resolved["ranking_type"] = current.get("ranking_type")

        # Change top-N only when the follow-up explicitly asks for a number.
        # Otherwise preserve the previous conversational limit.
        explicit_limit = re.search(
            r"\\b(?:top|first)\\s+(\\d+)\\b",
            question_lower,
        )

        if explicit_limit:
            resolved["limit"] = int(explicit_limit.group(1))
        elif previous.get("limit") is not None:
            resolved["limit"] = previous.get("limit")
    else:
        resolved = current

    result = answer_structured_question(question, understood=resolved)
    result["context"] = resolved
    return result


class AutoChatRequest(BaseModel):
    question: str
    context: dict | None = None


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
        r"\bfind\s+(?:player\s+)?[a-z]",
        r"\bsearch\s+(?:for\s+)?(?:player\s+)?[a-z]",
        r"\bhow many players?\b",
        r"\bnumber of players?\b",
        r"\bplayer count\b",
        r"\bdatabase count\b",
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
        r"\bplayer development\b",
        r"\bdevelopment matrix\b",
        r"\buploaded\b",
        r"\bdocument(s)?\b",
        r"\bpowerpoint\b",
        r"\bpptx?\b",
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

    # Preserve structured routing for short conversational follow-ups.
    # Existing structured context supplies the missing ranking details.
    if payload.context and route == "clarification":
        followup = question.lower().strip()

        if followup.startswith((
            "what about",
            "how about",
            "and ",
            "what is his",
            "what is her",
            "his ",
            "her ",
        )):
            route = "structured"

    if route == "structured":
        context_json = (
            json.dumps(payload.context)
            if payload.context
            else None
        )
        result = structured_chat(question, context=context_json)

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
