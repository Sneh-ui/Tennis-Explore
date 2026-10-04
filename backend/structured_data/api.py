from fastapi import FastAPI, HTTPException

from backend.structured_data.queries import (
    search_players,
    get_player_ranking_history,
    get_latest_player_rankings,
)
from backend.structured_data.structured_chat import answer_structured_question

app = FastAPI(
    title="Tennis EXPLORE Structured Data API",
    version="1.0.0",
)


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
