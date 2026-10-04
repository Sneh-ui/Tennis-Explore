import json

import requests
from backend.structured_data.queries import (
    search_players,
    fuzzy_search_players,
    get_player_ranking_history,
    get_latest_player_rankings,
)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"


def ask_ollama(prompt):
    """
    Send a prompt to the local Ollama model.
    """
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )

    response.raise_for_status()

    return response.json().get("response", "").strip()

def answer_latest_rankings(player_id):
    """
    Return the latest verified ranking/rating data from PostgreSQL.

    Values are formatted deterministically so the LLM cannot alter,
    omit, or misinterpret ranking and rating information.
    """
    rankings = get_latest_player_rankings(player_id)

    if not rankings:
        return "No ranking data was found for this player."

    lines = ["Latest available rankings and ratings:"]

    for row in rankings:
        source = row["source"]
        ranking_type = row["ranking_type"].title()
        snapshot_date = str(row["snapshot_date"])

        values = []

        if row["rank"] is not None:
            values.append(f"rank {row['rank']}")

        if row["points"] is not None:
            values.append(f"points {row['points']}")

        if row["rating"] is not None:
            values.append(f"rating {row['rating']}")

        if values:
            lines.append(
                f"- {source} {ranking_type}: "
                + ", ".join(values)
                + f" ({snapshot_date})"
            )

    return "\n".join(lines)

def format_ranking_history(rankings):
    """
    Convert database ranking rows into clean evidence for Ollama.
    Only fields that actually contain values are included.
    """
    formatted_rows = []

    for row in rankings:
        parts = [
            str(row["snapshot_date"]),
            row["source"],
            row["ranking_type"],
        ]

        if row["rank"] is not None:
            parts.append(f"rank: {row['rank']}")

        if row["points"] is not None:
            parts.append(f"points: {row['points']}")

        if row["rating"] is not None:
            parts.append(f"rating: {row['rating']}")

        formatted_rows.append(" | ".join(parts))

    return "\n".join(formatted_rows)


def answer_ranking_history(player_id):
    """
    Return ranking/rating history using verified PostgreSQL values.

    History is formatted deterministically in Python so ranking
    values, ratings, points, and dates are not altered by the LLM.
    """
    rankings = get_player_ranking_history(player_id)

    if not rankings:
        return "No ranking history was found for this player."

    grouped = {}

    for row in rankings:
        key = (row["source"], row["ranking_type"])
        grouped.setdefault(key, []).append(row)

    sections = []

    for (source, ranking_type), rows in grouped.items():
        heading = f"{source} {ranking_type.title()}"
        lines = [f"{heading}:"]

        for row in rows:
            date = str(row["snapshot_date"])
            values = []

            if row["rank"] is not None:
                values.append(f"rank {row['rank']}")

            if row["points"] is not None:
                values.append(f"points {row['points']}")

            if row["rating"] is not None:
                values.append(f"rating {row['rating']}")

            if values:
                lines.append(
                    f"- {date}: " + ", ".join(values)
                )

        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def resolve_player_name(name, limit=10):
    """
    Find possible players from a full, partial,
    or slightly misspelled name.

    The function avoids silently choosing between
    uncertain player matches.
    """
    name = name.strip()

    if not name:
        return {
            "status": "not_found",
            "players": [],
        }

    # First try normal database search.
    players = search_players(name, limit=limit)

    if not players:
        # If normal search fails, try fuzzy matching.
        fuzzy_players = fuzzy_search_players(name, limit=5)

        if not fuzzy_players:
            return {
                "status": "not_found",
                "players": [],
            }

        best = fuzzy_players[0]
        best_score = float(best["similarity_score"])

        second_score = (
            float(fuzzy_players[1]["similarity_score"])
            if len(fuzzy_players) > 1
            else 0.0
        )

        # Automatically accept only a strong
        # and clearly better fuzzy match.
        if (
            best_score >= 0.60
            and best_score - second_score >= 0.10
        ):
            return {
                "status": "matched",
                "player": best,
                "match_type": "fuzzy",
            }

        # Several possible fuzzy matches:
        # return them instead of guessing.
        return {
            "status": "ambiguous",
            "players": fuzzy_players,
            "match_type": "fuzzy",
        }

    # Check for an exact full-name match.
    exact_matches = [
        player
        for player in players
        if player["full_name"].lower() == name.lower()
    ]

    if len(exact_matches) == 1:
        return {
            "status": "matched",
            "player": exact_matches[0],
            "match_type": "exact",
        }

    # If normal search returned only one player,
    # the partial name safely identifies that player.
    if len(players) == 1:
        return {
            "status": "matched",
            "player": players[0],
            "match_type": "partial",
        }

    # Multiple normal-search results:
    # ask the user to clarify.
    return {
        "status": "ambiguous",
        "players": players,
        "match_type": "partial",
    }
def understand_question(question):
    """
    Use Ollama to identify the structured-data intent
    and player name from a natural-language question.
    """
    prompt = f"""
You are a routing assistant for Tennis EXPLORE.

Your job is ONLY to identify:
1. the user's intent;
2. the exact player-name text present in the user's question.

IMPORTANT:
- Copy the player name exactly as it appears in the user question.
- Never correct the spelling.
- Never expand a partial player name.
- Never infer a missing first name or surname.
- Never replace the entered name with a player you know.
- Do not check whether the player exists.
- Player identity will be resolved separately against the database.
- Do not answer the tennis question.
- Do not generate SQL.

Allowed intents:
- latest_rankings
- ranking_history
- unknown

Use "latest_rankings" when the user asks for the latest, current,
most recent, or available ranking/rating information for a player.

Use "ranking_history" when the user asks about ranking/rating history,
changes over time, previous rankings, or historical data.

Use "unknown" when the request does not fit those categories.

Return ONLY valid JSON containing:
- "intent"
- "player_name"

If no player name is present, use null for "player_name".

USER QUESTION:
{question}
""".strip()

    response = ask_ollama(prompt)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "intent": "unknown",
            "player_name": None,
        }
def answer_structured_question(question):
    """
    Understand a natural-language structured-data question
    and safely resolve the player against PostgreSQL.
    """
    understood = understand_question(question)

    intent = understood.get("intent")
    player_name = understood.get("player_name")

    if intent == "unknown":
        return {
            "status": "unsupported",
            "message": "I could not identify a supported structured-data question.",
        }

    if not player_name:
        return {
            "status": "missing_player",
            "message": "Please provide a player name.",
        }

    player_result = resolve_player_name(player_name)

    if player_result["status"] == "not_found":
        return {
            "status": "player_not_found",
            "message": f"No player could be matched to '{player_name}'.",
        }

    if player_result["status"] == "ambiguous":
        return {
            "status": "ambiguous_player",
            "player_name": player_name,
            "players": player_result["players"],
        }

    player = player_result["player"]
    player_id = player["player_id"]

    if intent == "latest_rankings":
        answer = answer_latest_rankings(player_id)

        return {
            "status": "answered",
            "intent": intent,
            "player": player,
            "match_type": player_result["match_type"],
            "answer": answer,
        }
    if intent == "ranking_history":
        answer = answer_ranking_history(player_id)

        return {
            "status": "answered",
            "intent": intent,
            "player": player,
            "match_type": player_result["match_type"],
            "answer": answer,
        }

    return {
        "status": "unsupported",
        "message": "This structured-data question is not supported yet.",
    }
