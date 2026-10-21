import os
import json
import re
import requests

from backend.structured_data.queries import (
    search_players,
    fuzzy_search_players,
    get_player_ranking_history,
    get_latest_player_rankings,
    get_filtered_player_rankings,
    get_best_player_ranking,
    get_top_ranked_players,
    get_top_ranked_players_in_period,
    get_ranking_date_range,
    get_player_profile,
    get_latest_filtered_player_rankings,
    get_player_count,
    get_players,
)

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate"
)
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")

SUPPORTED_INTENTS = {
    "latest_rankings",
    "ranking_history",
    "filtered_rankings",
    "best_ranking",
    "top_rankings",
    "player_profile",
    "player_count",
    "list_players",
    "general_tennis",
    "unknown",
}


def ask_ollama(prompt, json_mode=True):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    if json_mode:
        payload["format"] = "json"

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    result = response.json()
    answer = result.get("response", "").strip()

    if not answer:
        raise RuntimeError("Ollama returned an empty response.")

    return answer


def answer_general_tennis_question(question):
    prompt = f"""
You are Tennis Explore's helpful tennis assistant.

Answer the user's question directly, naturally, and helpfully.

You can help with:
- Beginner tennis advice
- Tennis footwork and movement
- Training and practice routines
- Tennis rules and techniques
- Fitness and match preparation
- Tennis equipment and basic guidance
- General tennis knowledge
- Tennis strategies and tactics

Instructions:
- Answer the actual question instead of asking for a player name unnecessarily.
- Give practical, beginner-friendly advice when appropriate.
- Use numbered steps or bullet points when useful.
- Explain technical concepts in simple language.
- Do not claim that general advice came from the database.
- Do not invent database rankings, statistics, or player records.
- If the question requires current rankings or specific database records,
  explain that the answer depends on the available structured data.
- If you are uncertain about a fact, say so instead of inventing information.
- Keep the answer relevant to the user's question.

User question:
{question}
""".strip()

    return ask_ollama(prompt, json_mode=False)


def answer_latest_rankings(
    player,
    source=None,
    ranking_type=None,
    requested_metric=None,
):
    rows = get_latest_filtered_player_rankings(
        player["player_id"],
        source=source,
        ranking_type=ranking_type,
    )

    name = player["full_name"]

    if not rows:
        requested = " ".join(
            value
            for value in [
                source.upper() if source else None,
                ranking_type.lower() if ranking_type else None,
                requested_metric,
            ]
            if value
        )

        if requested:
            return f"{requested.capitalize()} data is not available for {name}."

        return f"Ranking or rating data is not available for {name}."

    lines = []

    for row in rows:
        values = []

        if requested_metric == "ranking":
            if row.get("rank") is None:
                continue

            values.append(f"rank {row['rank']}")

        elif requested_metric == "rating":
            if row.get("rating") is None:
                continue

            values.append(f"rating {format_number(row['rating'])}")

        else:
            if row.get("rank") is not None:
                values.append(f"rank {row['rank']}")

            if row.get("points") is not None:
                values.append(f"{format_number(row['points'])} points")

            if row.get("rating") is not None:
                values.append(f"rating {format_number(row['rating'])}")

        if values:
            lines.append(
                f"- {row['source']} {row['ranking_type'].title()}: "
                f"{', '.join(values)} "
                f"({format_date(row['snapshot_date'])})"
            )

    if not lines:
        metric = requested_metric or "requested"
        requested_source = f"{source.upper()} " if source else ""

        return (
            f"{requested_source}{metric} data is not available "
            f"for {name}."
        )

    if requested_metric == "ranking":
        heading = (
            f"{name}'s latest available {source.upper()} rankings:"
            if source
            else f"{name}'s latest available rankings:"
        )

    elif requested_metric == "rating":
        heading = (
            f"{name}'s latest available {source.upper()} ratings:"
            if source
            else f"{name}'s latest available ratings:"
        )

    else:
        heading = (
            f"{name}'s latest available {source.upper()} ranking and rating data:"
            if source
            else f"{name}'s latest available ranking and rating data:"
        )

    return heading + "\n" + "\n".join(lines)


def format_ranking_history(rankings):
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


def answer_ranking_history(
    player_id,
    source=None,
    ranking_type=None,
):
    rankings = get_player_ranking_history(player_id)

    if source:
        rankings = [
            row for row in rankings
            if row["source"].upper() == source.upper()
        ]

    if ranking_type:
        rankings = [
            row for row in rankings
            if row["ranking_type"].lower() == ranking_type.lower()
        ]

    if not rankings:
        requested = " ".join(
            value
            for value in [
                source.upper() if source else None,
                ranking_type.lower() if ranking_type else None,
            ]
            if value
        )

        if requested:
            return (
                f"{requested} ranking or rating history "
                f"is not available for this player."
            )

        return "Ranking or rating history is not available for this player."

    grouped = {}

    for row in rankings:
        key = (row["source"], row["ranking_type"])
        grouped.setdefault(key, []).append(row)

    sections = []

    for (row_source, row_ranking_type), rows in grouped.items():
        lines = [f"{row_source} {row_ranking_type.title()}:"]

        for row in rows:
            values = []

            if row["rank"] is not None:
                values.append(f"rank {row['rank']}")

            if row["points"] is not None:
                values.append(f"{format_number(row['points'])} points")

            if row["rating"] is not None:
                values.append(f"rating {format_number(row['rating'])}")

            if values:
                lines.append(
                    f"- {format_date(row['snapshot_date'])}: "
                    + ", ".join(values)
                )

        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def resolve_player_name(name, limit=10):
    name = (name or "").strip()

    if not name:
        return {
            "status": "not_found",
            "players": [],
        }

    players = search_players(name, limit=limit)

    if not players:
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

        if best_score >= 0.60 and best_score - second_score >= 0.10:
            return {
                "status": "matched",
                "player": best,
                "match_type": "fuzzy",
            }

        if best_score < 0.35:
            return {
                "status": "not_found",
                "players": [],
            }

        meaningful_players = [
            player
            for player in fuzzy_players
            if float(player["similarity_score"]) >= 0.35
        ]

        if not meaningful_players:
            return {
                "status": "not_found",
                "players": [],
            }

        return {
            "status": "ambiguous",
            "players": meaningful_players,
            "match_type": "fuzzy",
        }

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

    if len(players) == 1:
        return {
            "status": "matched",
            "player": players[0],
            "match_type": "partial",
        }

    return {
        "status": "ambiguous",
        "players": players,
        "match_type": "partial",
    }


def _extract_json_object(response):
    response = (response or "").strip()

    if response.startswith("```"):
        response = re.sub(
            r"^```(?:json)?\s*",
            "",
            response,
            flags=re.IGNORECASE,
        )
        response = re.sub(r"\s*```$", "", response)

    try:
        parsed = json.loads(response)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = response.find("{")

    if start != -1:
        try:
            parsed, _ = json.JSONDecoder().raw_decode(response[start:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {}


def _extract_player_name(question):
    text = (question or "").strip()

    patterns = [
        r"^\s*who\s+is\s+(.+?)\s*[?.!]*\s*$",
        r"^\s*who\s+was\s+(.+?)\s*[?.!]*\s*$",
        r"^\s*tell\s+me\s+about\s+(.+?)\s*[?.!]*\s*$",
        r"^\s*show\s+me\s+(.+?)\s*[?.!]*\s*$",
        r"^\s*find\s+(.+?)\s*[?.!]*\s*$",
        r"^\s*give\s+me\s+the\s+profile\s+of\s+(.+?)\s*[?.!]*\s*$",
        r"^\s*what\s+is\s+the\s+profile\s+of\s+(.+?)\s*[?.!]*\s*$",
        r"^\s*what\s+is\s+(.+?)'s\s+(?:latest\s+|current\s+|most\s+recent\s+)?"
        r"(?:atp|wta|itf|utr\s+)?(?:singles\s+|doubles\s+)?"
        r"(?:ranking|rank|rating|profile)\s*[?.!]*\s*$",
        r"^\s*(?:what\s+is|what's)\s+the\s+"
        r"(?:latest\s+|current\s+|most\s+recent\s+)?"
        r"(?:atp|wta|itf|utr\s+)?(?:singles\s+|doubles\s+)?"
        r"(?:ranking|rank|rating)\s+of\s+(.+?)\s*[?.!]*\s*$",
        r"^\s*(?:latest|current|recent)\s+"
        r"(?:atp|wta|itf|utr\s+)?(?:singles\s+|doubles\s+)?"
        r"(?:ranking|rank|rating)\s+of\s+(.+?)\s*[?.!]*\s*$",
        r"^\s*(?:ranking|rank|rating)\s+of\s+(.+?)\s*[?.!]*\s*$",
    ]

    for pattern in patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)

        if match:
            candidate = match.group(1).strip(" \t\r\n?.!,")
            candidate = re.sub(
                r"\s+(?:today|currently|right now)$",
                "",
                candidate,
                flags=re.IGNORECASE,
            ).strip()

            if candidate:
                return candidate

    return None


def _fallback_intent(question, understood=None):
    text = (question or "").lower()
    understood = understood or {}

    source = understood.get("source")
    ranking_type = understood.get("ranking_type")

    if re.search(r"\bhow many players\b|\bplayer count\b|\btotal players\b", text):
        return "player_count"

    if re.search(r"\b(list|show|display)\b.*\bplayers\b", text):
        if not source and not re.search(r"\b(top|ranked|ranking)\b", text):
            return "list_players"

    if re.search(
        r"\btop\s+\d*\s*players\b|\btop-ranked players\b|\btop ranked players\b",
        text,
    ):
        return "top_rankings"

    if re.search(r"\b(best|highest|peak|career-best|career best)\b", text):
        if re.search(r"\b(rank|ranking|rating)\b", text):
            return "best_ranking"

    if re.search(r"\b(average|mean)\b", text):
        if re.search(r"\b(rank|ranking|rating)\b", text):
            return "ranking_history"

    if re.search(
        r"\b(compare|comparison|improve|improved|decline|declined|"
        r"change|changed|increase|increased|decrease|decreased)\b",
        text,
    ):
        if re.search(r"\b(rank|ranking|rating)\b", text):
            return "ranking_history"

    if re.search(r"\b(history|historical|over time|trend)\b", text):
        if re.search(r"\b(rank|ranking|rating)\b", text):
            return "ranking_history"

    if re.search(r"\b(atp|wta|itf|utr)\b", text) and re.search(
        r"\b(rank|ranking|rating)\b",
        text,
    ):
        if re.search(r"\b(best|highest|peak|career-best|career best)\b", text):
            return "best_ranking"

        if re.search(
            r"\b(history|historical|between|from|during|in \d{4}|on \d{1,2}\b)",
            text,
        ):
            return "filtered_rankings"

        if re.search(r"\b(top|top-ranked|top ranked)\b", text):
            return "top_rankings"

        if re.search(r"\b(latest|current|recent|today|now)\b", text):
            return "latest_rankings"

        if source or ranking_type:
            return "filtered_rankings"

    if re.search(
        r"\b(latest|current|recent|most recent)\b",
        text,
    ) and re.search(r"\b(rank|ranking|rating)\b", text):
        return "latest_rankings"

    if re.search(r"\b(rank|ranking|rating)\b", text):
        if re.search(r"\b(of|for)\b", text):
            return "latest_rankings"

    if re.search(
        r"\b(who is|who was|tell me about|player profile|"
        r"country|nationality|born|birth year|gender|represents)\b",
        text,
    ):
        return "player_profile"

    if re.match(r"^\s*who\s+is\s+.+", text):
        return "player_profile"

    if not re.search(
        r"\b(rank|ranking|rating|ranked|database|"
        r"player count|list players|top players|career-best)\b",
        text,
    ) and re.search(
        r"\b(how can|how do|how should|how to|tips|beginner|"
        r"footwork|training|practice|technique|improve my|"
        r"improve your|tennis rules|tennis strategy|"
        r"tennis tactics|workout|warm.?up|serve technique|"
        r"backhand|forehand|volley|fitness|match preparation)\b",
        text,
    ):
        return "general_tennis"

    return "unknown"


def understand_question(question):
    prompt = f"""
You are a routing assistant for Tennis EXPLORE.

Identify the user's intent using ONLY the allowed intents below.
Do not answer the question. Do not invent facts or dates.
Copy any player name exactly as entered.

Allowed intents:
- latest_rankings
- ranking_history
- filtered_rankings
- best_ranking
- top_rankings
- player_profile
- player_count
- list_players
- general_tennis
- unknown

Rules:
- Latest/current/most recent player ranking or rating:
  latest_rankings.
- Ranking or rating history over time:
  ranking_history.
- Ranking/rating with a specified organisation, ranking type,
  date, month, year, or date range:
  filtered_rankings.
- Best, highest, peak, or career-best numerical ranking:
  best_ranking.
- Top-ranked players, such as the top 5 ATP singles players:
  top_rankings.
- Basic information about one player, or "Who is [name]?":
  player_profile.
- Number of players in the database:
  player_count.
- List players without asking for a ranking:
  list_players.
- General tennis advice, beginner guidance, footwork, training,
  technique, tennis rules, strategy, fitness, or practice questions
  that do not require specific database records:
  general_tennis.
- Match statistics such as aces, double faults, winners,
  unforced errors, serve percentage, break points, match scores,
  or shot statistics:
  unknown.
- Questions about a specific player's database profile or rankings
  must use the appropriate structured-data intent, not general_tennis.
- Use unknown for questions unrelated to tennis or unsupported
  database information.

Sources: ATP, WTA, ITF, UTR.
Ranking types: singles, doubles.
Only use a source or ranking type if it is mentioned in the question.
For UTR ratings, do not assume a ranking type.
Copy the player's name exactly; never invent or correct it.
For general player lists, use limit 10 if no number is specified.
For top rankings, use limit 5 if no number is specified.
For all other questions, use null for limit unless a number is requested.
Dates must be YYYY-MM-DD when an exact date is explicitly stated.
Do not guess dates.

Use "filtered_rankings" when the user asks for ranking or
rating information for a particular source, ranking type,
date, month, year, or date range.

Use "best_ranking" when the user asks for the player's best,
highest, peak, or career-best numerical ranking.

Use "top_rankings" when the user asks who the top-ranked
players are, for example top 5 ATP singles players.

Use "player_profile" for basic player information such as
country, gender, birth year, or when the user asks to find,
show, or identify one specific player.

Use "player_count" when the user asks how many players are
in the database or asks for the total number of players.

Use "list_players" when the user asks to show, list, or display
a number of players from the database without requesting a
ranking organisation. Put the requested number in "limit".
If no number is given for a general player list, use 10.

The structured database does NOT contain match statistics such as
aces, double faults, winners, unforced errors, serve percentage,
break points, match scores, or shot statistics.

Questions asking for those values MUST use "unknown", even when
a player name is present.

A question about a specific organisation such as ATP, WTA, ITF or UTR
is still a supported structured-data question even if that player may
not have data from that organisation. Do NOT use "unknown" simply
because the requested organisation may be unavailable.

For example:
"What is Cruz Hewitt's WTA singles ranking?"
must be classified as "filtered_rankings" with source "WTA" and
ranking_type "singles". The database will determine whether data exists.

Use "unknown" if the question cannot be answered using
player identity/profile or ranking/rating data.

Dates:
- Return dates as YYYY-MM-DD when an exact date is clearly stated.
- If a whole month is requested, return the first day as
  start_date and the last day as end_date.
- If a whole year is requested, return January 1 of that year as
  start_date and December 31 of that year as end_date.
- If no date is requested, use null.
- Do not guess an unspecified date.

For top-N questions:
- Return the requested number as "limit".
- If the user says "top players" without a number, use 5.
- For top-ranking questions, return the requested number as "limit".
- For general player-list questions, also return the requested number as "limit".
- If the user asks to list/show players without a number, use 10.
- Otherwise use null.

Return ONLY valid JSON with exactly these keys:
{{
  "intent": "unknown",
  "player_name": null,
  "source": null,
  "ranking_type": null,
  "start_date": null,
  "end_date": null,
  "limit": null
}}

Replace the values with the correct extracted values.

USER QUESTION:
{question}
""".strip()

    response = ask_ollama(prompt, json_mode=True)
    data = _extract_json_object(response)

    intent = data.get("intent")

    if not isinstance(intent, str) or intent not in SUPPORTED_INTENTS:
        intent = "unknown"

    player_name = data.get("player_name")
    if not isinstance(player_name, str) or not player_name.strip():
        player_name = None
    else:
        player_name = player_name.strip()

    source = data.get("source")
    if isinstance(source, str):
        source = source.strip().upper()
        if source not in {"ATP", "WTA", "ITF", "UTR"}:
            source = None
    else:
        source = None

    ranking_type = data.get("ranking_type")
    if isinstance(ranking_type, str):
        ranking_type = ranking_type.strip().lower()
        if ranking_type not in {"singles", "doubles"}:
            ranking_type = None
    else:
        ranking_type = None

    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not isinstance(start_date, str) or not start_date.strip():
        start_date = None

    if not isinstance(end_date, str) or not end_date.strip():
        end_date = None

    limit = data.get("limit")
    try:
        limit = int(limit) if limit is not None else None
    except (TypeError, ValueError):
        limit = None

    question_lower = question.lower()

    if not source:
        source_match = re.search(r"\b(atp|wta|itf|utr)\b", question_lower)
        if source_match:
            source = source_match.group(1).upper()

    if not ranking_type:
        type_match = re.search(r"\b(singles|doubles)\b", question_lower)
        if type_match:
            ranking_type = type_match.group(1).lower()

    if not player_name:
        player_name = _extract_player_name(question)

    if not limit:
        limit_match = re.search(r"\btop\s+(\d+)\b", question_lower)
        if not limit_match:
            limit_match = re.search(
                r"\b(?:list|show|display)\s+(\d+)\s+players\b",
                question_lower,
            )

        if limit_match:
            limit = int(limit_match.group(1))

    if intent == "unknown":
        intent = _fallback_intent(
            question,
            {
                "source": source,
                "ranking_type": ranking_type,
            },
        )

    if (
        intent == "latest_rankings"
        and re.search(r"\b(atp|wta|itf|utr)\b", question_lower)
        and re.search(r"\b(on|between|during|from)\b", question_lower)
    ):
        intent = "filtered_rankings"

    return {
        "intent": intent,
        "player_name": player_name,
        "source": source,
        "ranking_type": ranking_type,
        "start_date": start_date,
        "end_date": end_date,
        "limit": limit,
    }


def merge_followup_context(current, previous=None):
    """Merge a short follow-up with the previous resolved structured state."""
    if not previous:
        return current

    merged = dict(previous)

    # The current turn overrides only fields it explicitly resolved.
    for key in (
        "intent",
        "player_name",
        "source",
        "ranking_type",
        "start_date",
        "end_date",
        "limit",
    ):
        value = current.get(key)
        if value is not None and value != "unknown":
            merged[key] = value

    return merged


def format_date(value):
    if value is None:
        return ""

    if isinstance(value, str):
        from datetime import date
        value = date.fromisoformat(value)

    return value.strftime("%-d %B %Y")


def format_number(value):
    if value is None:
        return None

    number = float(value)

    if number.is_integer():
        return str(int(number))

    return f"{number:.2f}".rstrip("0").rstrip(".")


def describe_record(row):
    values = []

    if row.get("rank") is not None:
        values.append(f"rank {row['rank']}")

    if row.get("points") is not None:
        values.append(f"{format_number(row['points'])} points")

    if row.get("rating") is not None:
        values.append(f"rating {format_number(row['rating'])}")

    return ", ".join(values)


def answer_filtered_rankings(
    player,
    source=None,
    ranking_type=None,
    start_date=None,
    end_date=None,
):
    rows = get_filtered_player_rankings(
        player["player_id"],
        source=source,
        ranking_type=ranking_type,
        start_date=start_date,
        end_date=end_date,
    )

    name = player["full_name"]

    if not rows:
        requested = " ".join(
            value
            for value in [
                source.upper() if source else None,
                ranking_type.lower() if ranking_type else None,
            ]
            if value
        )

        if start_date and end_date and start_date == end_date:
            if requested:
                return (
                    f"{requested} ranking data is not available for "
                    f"{name} on {format_date(start_date)}."
                )

            return (
                f"Ranking data is not available for {name} on "
                f"{format_date(start_date)}."
            )

        if requested:
            return f"{requested} ranking data is not available for {name}."

        return f"Ranking data is not available for {name}."

    lines = []

    for row in rows:
        value = describe_record(row)

        if value:
            lines.append(
                f"- {format_date(row['snapshot_date'])}: "
                f"{row['source']} {row['ranking_type'].title()} — {value}"
            )

    if not lines:
        return (
            f"The requested ranking or rating information "
            f"is not available for {name}."
        )

    if start_date and end_date:
        if start_date == end_date:
            period = f"on {format_date(start_date)}"
        else:
            period = (
                f"from {format_date(start_date)} "
                f"to {format_date(end_date)}"
            )
    elif start_date:
        period = f"on {format_date(start_date)}"
    elif end_date:
        period = f"up to {format_date(end_date)}"
    else:
        period = "in the available data"

    if source and ranking_type:
        heading = (
            f"{name}'s available {source.upper()} "
            f"{ranking_type.lower()} data {period}:"
        )
    elif source:
        heading = (
            f"{name}'s available {source.upper()} data {period}:"
        )
    else:
        heading = (
            f"{name}'s available ranking and rating data {period}:"
        )

    return heading + "\n" + "\n".join(lines)


def answer_best_ranking(player, source=None, ranking_type=None):
    row = get_best_player_ranking(
        player["player_id"],
        source=source,
        ranking_type=ranking_type,
    )

    name = player["full_name"]

    if not row:
        requested = " ".join(
            value
            for value in [
                source.upper() if source else None,
                ranking_type.lower() if ranking_type else None,
            ]
            if value
        )

        if requested:
            return f"{requested} ranking data is not available for {name}."

        return f"Ranking data is not available for {name}."

    return (
        f"{name}'s best {row['source']} "
        f"{row['ranking_type'].lower()} ranking in the available data "
        f"is {row['rank']}, recorded on "
        f"{format_date(row['snapshot_date'])}."
    )


def answer_ranking_change(
    player,
    source=None,
    ranking_type=None,
    start_date=None,
    end_date=None,
    requested_metric="ranking",
):
    rows = get_filtered_player_rankings(
        player["player_id"],
        source=source,
        ranking_type=ranking_type,
        start_date=start_date,
        end_date=end_date,
    )

    name = player["full_name"]

    if requested_metric == "rating":
        rows = [row for row in rows if row.get("rating") is not None]
        value_key = "rating"
    else:
        rows = [row for row in rows if row.get("rank") is not None]
        value_key = "rank"

    if len(rows) < 2:
        return (
            f"There is not enough {requested_metric} data available "
            f"to calculate a change for {name}."
        )

    first = rows[0]
    last = rows[-1]

    first_value = float(first[value_key])
    last_value = float(last[value_key])

    if requested_metric == "ranking":
        difference = first_value - last_value

        if difference > 0:
            change_text = (
                f"improved by {format_number(abs(difference))} positions"
            )
        elif difference < 0:
            change_text = (
                f"declined by {format_number(abs(difference))} positions"
            )
        else:
            change_text = "did not change"

        return (
            f"{name}'s {first['source']} "
            f"{first['ranking_type'].lower()} ranking {change_text}, "
            f"from {format_number(first_value)} on "
            f"{format_date(first['snapshot_date'])} to "
            f"{format_number(last_value)} on "
            f"{format_date(last['snapshot_date'])}."
        )

    difference = last_value - first_value

    if difference > 0:
        change_text = f"increased by {format_number(abs(difference))}"
    elif difference < 0:
        change_text = f"decreased by {format_number(abs(difference))}"
    else:
        change_text = "did not change"

    return (
        f"{name}'s {first['source']} "
        f"{first['ranking_type'].lower()} rating {change_text}, "
        f"from {format_number(first_value)} on "
        f"{format_date(first['snapshot_date'])} to "
        f"{format_number(last_value)} on "
        f"{format_date(last['snapshot_date'])}."
    )


def answer_average_ranking(
    player,
    source=None,
    ranking_type=None,
    start_date=None,
    end_date=None,
):
    name = player["full_name"]

    if not start_date or not end_date:
        return (
            f"Please specify a period for calculating "
            f"{name}'s average ranking."
        )

    rows = get_filtered_player_rankings(
        player["player_id"],
        source=source,
        ranking_type=ranking_type,
        start_date=start_date,
        end_date=end_date,
    )

    rows = [row for row in rows if row.get("rank") is not None]

    if not rows:
        return (
            f"Ranking data is not available for {name} "
            f"in the requested period."
        )

    combinations = {
        (row["source"], row["ranking_type"])
        for row in rows
    }

    if len(combinations) > 1:
        return (
            "Please specify one ranking organisation and ranking type "
            "for the average, for example ATP singles."
        )

    average = sum(float(row["rank"]) for row in rows) / len(rows)
    first = rows[0]

    return (
        f"{name}'s average {first['source']} "
        f"{first['ranking_type'].lower()} ranking from "
        f"{format_date(start_date)} to {format_date(end_date)} "
        f"is {format_number(average)}, based on "
        f"{len(rows)} available ranking snapshots."
    )


def answer_period_comparison(
    player,
    source=None,
    ranking_type=None,
    start_date=None,
    end_date=None,
    requested_metric="ranking",
):
    if not start_date or not end_date:
        return answer_ranking_change(
            player,
            source=source,
            ranking_type=ranking_type,
            start_date=start_date,
            end_date=end_date,
            requested_metric=requested_metric,
        )

    from datetime import date
    import calendar

    start_value = date.fromisoformat(str(start_date))
    end_value = date.fromisoformat(str(end_date))

    start_month_end = date(
        start_value.year,
        start_value.month,
        calendar.monthrange(start_value.year, start_value.month)[1],
    )

    end_month_start = date(
        end_value.year,
        end_value.month,
        1,
    )

    end_month_end = date(
        end_value.year,
        end_value.month,
        calendar.monthrange(end_value.year, end_value.month)[1],
    )

    first_rows = get_filtered_player_rankings(
        player["player_id"],
        source=source,
        ranking_type=ranking_type,
        start_date=start_value,
        end_date=start_month_end,
    )

    second_rows = get_filtered_player_rankings(
        player["player_id"],
        source=source,
        ranking_type=ranking_type,
        start_date=end_month_start,
        end_date=end_month_end,
    )

    value_key = "rating" if requested_metric == "rating" else "rank"

    first_rows = [
        row for row in first_rows
        if row.get(value_key) is not None
    ]

    second_rows = [
        row for row in second_rows
        if row.get(value_key) is not None
    ]

    name = player["full_name"]

    if not first_rows or not second_rows:
        return (
            f"There is not enough {requested_metric} data available "
            f"to compare those periods for {name}."
        )

    first = first_rows[-1]
    second = second_rows[-1]

    first_number = float(first[value_key])
    second_number = float(second[value_key])

    if requested_metric == "ranking":
        difference = first_number - second_number

        if difference > 0:
            change = (
                f"an improvement of {format_number(difference)} positions"
            )
        elif difference < 0:
            change = (
                f"a decline of {format_number(abs(difference))} positions"
            )
        else:
            change = "no change"
    else:
        difference = second_number - first_number

        if difference > 0:
            change = f"an increase of {format_number(difference)}"
        elif difference < 0:
            change = f"a decrease of {format_number(abs(difference))}"
        else:
            change = "no change"

    return (
        f"{name}'s {first['source']} "
        f"{first['ranking_type'].lower()} {requested_metric} was "
        f"{format_number(first_number)} on "
        f"{format_date(first['snapshot_date'])} and "
        f"{format_number(second_number)} on "
        f"{format_date(second['snapshot_date'])}, "
        f"which is {change}."
    )


def answer_player_count():
    total = get_player_count()
    return f"There are {total:,} players in the structured database."


def answer_player_list(limit=10):
    limit = limit or 10
    limit = max(1, min(int(limit), 100))

    rows = get_players(limit=limit)

    if not rows:
        return "No players are available in the structured database."

    lines = [f"Here are {len(rows)} players from the database:"]

    for index, row in enumerate(rows, start=1):
        details = []

        if row.get("country"):
            country = format_country(row["country"])
            if country:
                details.append(country)

        if row.get("birth_year"):
            details.append(str(row["birth_year"]))

        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(f"{index}. {row['full_name']}{suffix}")

    return "\n".join(lines)


def answer_top_rankings(
    source,
    ranking_type="singles",
    limit=5,
    snapshot_date=None,
    start_date=None,
    end_date=None,
):
    if not source:
        return "Please specify a ranking organisation such as ATP, WTA, ITF or UTR."

    ranking_type = ranking_type or "singles"

    availability = get_ranking_date_range(source, ranking_type)

    if not availability:
        return (
            f"{source.upper()} {ranking_type.lower()} "
            f"ranking data is not available in the database."
        )

    min_date = availability["min_date"]
    max_date = availability["max_date"]

    requested_start = start_date or snapshot_date
    requested_end = end_date or snapshot_date

    # Reject requests completely outside the available DB period.
    if requested_start and requested_end:
        from datetime import date

        if isinstance(requested_start, str):
            requested_start_value = date.fromisoformat(requested_start)
        else:
            requested_start_value = requested_start

        if isinstance(requested_end, str):
            requested_end_value = date.fromisoformat(requested_end)
        else:
            requested_end_value = requested_end

        if requested_end_value < min_date or requested_start_value > max_date:
            if (
                requested_start_value.month == 1
                and requested_start_value.day == 1
                and requested_end_value.month == 12
                and requested_end_value.day == 31
                and requested_start_value.year == requested_end_value.year
            ):
                requested_period = str(requested_start_value.year)
            elif (
                requested_start_value.year == requested_end_value.year
                and requested_start_value.month == requested_end_value.month
                and requested_start_value.day == 1
            ):
                requested_period = requested_start_value.strftime("%B %Y")
            elif requested_start_value == requested_end_value:
                requested_period = format_date(requested_start_value)
            else:
                requested_period = (
                    f"{format_date(requested_start_value)} to "
                    f"{format_date(requested_end_value)}"
                )

            return (
                f"{source.upper()} {ranking_type.lower()} ranking data for "
                f"{requested_period} is not available in the database. "
                f"Available {source.upper()} {ranking_type.lower()} data covers "
                f"{format_date(min_date)} to {format_date(max_date)}."
            )

    # Period request: choose the latest real snapshot inside that period.
    if start_date or end_date:
        rows = get_top_ranked_players_in_period(
            source,
            ranking_type=ranking_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit or 5,
        )
    else:
        rows = get_top_ranked_players(
            source,
            ranking_type=ranking_type,
            snapshot_date=snapshot_date,
            limit=limit or 5,
        )

    if not rows:
        if requested_start or requested_end:
            period_parts = []

            if requested_start:
                period_parts.append(format_date(requested_start))

            if requested_end and requested_end != requested_start:
                period_parts.append(format_date(requested_end))

            requested_period = " to ".join(period_parts)

            return (
                f"{source.upper()} {ranking_type.lower()} ranking data is not "
                f"available for {requested_period}. "
                f"Available {source.upper()} {ranking_type.lower()} data covers "
                f"{format_date(min_date)} to {format_date(max_date)}."
            )

        return (
            f"{source.upper()} {ranking_type.lower()} "
            f"ranking data is not available."
        )

    actual_date = format_date(rows[0]["snapshot_date"])

    if len(rows) == 1:
        row = rows[0]

        country = (
            f" ({format_country(row['country'])})"
            if row.get("country")
            else ""
        )

        if snapshot_date or start_date or end_date:
            return (
                f"{row['full_name']}{country} was ranked number "
                f"{row['rank']} in {source.upper()} "
                f"{ranking_type.lower()} on {actual_date}."
            )

        return (
            f"{row['full_name']}{country} is ranked number "
            f"{row['rank']} in the latest {source.upper()} "
            f"{ranking_type.lower()} ranking available in the database "
            f"({actual_date})."
        )

    if snapshot_date or start_date or end_date:
        intro = (
            f"In the {source.upper()} {ranking_type.lower()} ranking "
            f"available on {actual_date}, the top {len(rows)} players are:"
        )
    else:
        intro = (
            f"In the latest {source.upper()} {ranking_type.lower()} ranking "
            f"available in the database ({actual_date}), "
            f"the top {len(rows)} players are:"
        )

    lines = [intro]

    for row in rows:
        country = (
            f" ({format_country(row['country'])})"
            if row.get("country")
            else ""
        )
        lines.append(f"{row['rank']}. {row['full_name']}{country}")

    return "\n".join(lines)


def answer_player_profile(player, question):
    profile = get_player_profile(player["player_id"])

    if not profile:
        return "Player information is not available."

    name = profile["full_name"]
    question_lower = question.lower()

    if "country" in question_lower or "represent" in question_lower:
        if profile.get("country"):
            country = format_country(profile["country"])
            return f"{name} represents {country}."

        return f"Country information is not available for {name}."

    if "birth" in question_lower or "born" in question_lower:
        if profile.get("birth_year"):
            return f"{name}'s birth year is {profile['birth_year']}."

        return f"Birth-year information is not available for {name}."

    if "gender" in question_lower:
        if profile.get("gender"):
            return f"{name}'s recorded gender is {profile['gender']}."

        return f"Gender information is not available for {name}."

    details = []

    if profile.get("country"):
        details.append(f"Country: {format_country(profile['country'])}")

    if profile.get("gender"):
        details.append(f"Gender: {profile['gender']}")

    if profile.get("birth_year"):
        details.append(f"Birth year: {profile['birth_year']}")

    if details:
        return f"{name}\n" + "\n".join(
            f"- {detail}" for detail in details
        )

    return (
        f"{name} was found in the player database, "
        f"but additional profile information is not available."
    )


def format_country(country):
    if not country:
        return None

    country_names = {
        "AUS": "Australia",
        "USA": "United States",
        "GBR": "Great Britain",
        "ITA": "Italy",
        "ESP": "Spain",
        "GER": "Germany",
        "FRA": "France",
        "CAN": "Canada",
        "SRB": "Serbia",
        "SUI": "Switzerland",
        "POL": "Poland",
        "BLR": "Belarus",
        "KAZ": "Kazakhstan",
        "CZE": "Czech Republic",
        "CHN": "China",
        "JPN": "Japan",
        "KOR": "South Korea",
        "NZL": "New Zealand",
    }

    return country_names.get(country.upper(), country)
def answer_structured_question(question, understood=None):
    # Parse normally for standalone questions. For conversational
    # follow-ups, the API can provide an already-resolved context.
    if understood is None:
        understood = understand_question(question)

    # The ranking dataset used by Tennis EXPLORE covers 2026.
    # If the user names a month without an explicit year, the language
    # router can invent a year (for example 2000 or 2022). Normalise
    # month-only ranking questions deterministically to 2026.
    question_lower = question.lower()

    month_numbers = {
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

    has_explicit_year = any(
        str(year) in question_lower
        for year in range(1900, 2101)
    )

    if not has_explicit_year:
        from datetime import date, timedelta

        for month_name, month_number in month_numbers.items():
            if month_name in question_lower:
                year = 2026

                if month_number == 12:
                    next_year, next_month = 2027, 1
                else:
                    next_year, next_month = year, month_number + 1

                understood["start_date"] = date(
                    year, month_number, 1
                ).isoformat()

                understood["end_date"] = (
                    date(next_year, next_month, 1)
                    - timedelta(days=1)
                ).isoformat()
                break

    intent = understood.get("intent", "unknown")
    player_name = understood.get("player_name")
    source = understood.get("source")
    ranking_type = understood.get("ranking_type")
    start_date = understood.get("start_date")
    end_date = understood.get("end_date")
    limit = understood.get("limit")

    question_lower = question.lower()

    if intent == "general_tennis":
        try:
            answer = answer_general_tennis_question(question)
            return {
                "status": "answered",
                "answer": answer,
            }
        except requests.RequestException:
            return {
                "status": "error",
                "answer": (
                    "I'm unable to generate a tennis answer right now. "
                    "Please try again shortly."
                ),
            }
        except RuntimeError:
            return {
                "status": "error",
                "answer": (
                    "The tennis assistant is temporarily unavailable. "
                    "Please try again later."
                ),
            }

    if (
        start_date
        and not end_date
        and re.search(r"\bon\b", question_lower)
    ):
        end_date = start_date
    question_lower = question.lower()

    # Explicit ranking requests such as "Show me the top 10 WTA players"
    # must use ranking data rather than the generic alphabetical player list.
    import re

    explicit_top_ranking = re.search(
        r"\btop\s+(\d+)\s+(atp|wta|itf|utr)\b",
        question_lower,
        re.IGNORECASE,
    )

    if explicit_top_ranking:
        intent = "top_rankings"
        source = explicit_top_ranking.group(2).upper()
        limit = int(explicit_top_ranking.group(1))

        # Product rule: when singles/doubles is not explicitly stated,
        # ranking queries default to singles.
        if "doubles" in question_lower:
            ranking_type = "doubles"
        elif "singles" in question_lower:
            ranking_type = "singles"
        else:
            ranking_type = "singles"

    requested_metric = None

    if re.search(r"\brating\b", question_lower):
        requested_metric = "rating"
    elif re.search(r"\branking\b|\brank\b", question_lower):
        requested_metric = "ranking"

    wants_average = bool(
        re.search(r"\baverage\b|\bmean\b", question_lower)
    )

    wants_comparison = bool(
        re.search(r"\bcompare\b|\bcompared\b|\bcomparison\b", question_lower)
    )

    wants_change = bool(
        re.search(
            r"\b(improved|improve|declined|decline|changed|change|"
            r"increased|increase|decreased|decrease)\b",
            question_lower,
        )
    )

    unsupported_terms = {
        "double fault": "Double-fault",
        "double faults": "Double-fault",
        "unforced error": "Unforced-error",
        "unforced errors": "Unforced-error",
        "serve percentage": "Serve-percentage",
        "break point": "Break-point",
        "break points": "Break-point",
        "matches won": "Match win/loss",
        "match wins": "Match win/loss",
        "wins": "Match win/loss",
        "losses": "Match win/loss",
        "win loss": "Match win/loss",
        "win/loss": "Match win/loss",
        "aces": "Aces",
        "ace": "Aces",
        "winners": "Winner",
        "winner": "Winner",
        "match score": "Match-score",
        "match scores": "Match-score",
        "shot statistics": "Shot-statistics",
    }

    for term, label in unsupported_terms.items():
        if re.search(rf"\b{re.escape(term)}\b", question_lower):
            return {
                "status": "unsupported",
                "answer": (
                    f"{label} information is not available "
                    f"in the structured data."
                ),
            }

    if "overall" in question_lower and (
        "top" in question_lower
        or "best" in question_lower
        or "ranking" in question_lower
        or "ranked" in question_lower
    ):
        return {
            "status": "clarification_needed",
            "answer": (
                "By overall, do you mean the latest ranking, "
                "the best ranking achieved, or the average ranking "
                "over a particular period?"
            ),
        }

    if intent == "unknown":
        intent = _fallback_intent(
            question,
            {
                "source": source,
                "ranking_type": ranking_type,
            },
        )

    if intent == "general_tennis":
        try:
            answer = answer_general_tennis_question(question)
            return {
                "status": "answered",
                "answer": answer,
            }
        except requests.RequestException:
            return {
                "status": "error",
                "answer": (
                    "I'm unable to generate a tennis answer right now. "
                    "Please try again shortly."
                ),
            }
        except RuntimeError:
            return {
                "status": "error",
                "answer": (
                    "The tennis assistant is temporarily unavailable. "
                    "Please try again later."
                ),
            }

    if not player_name:
        player_name = _extract_player_name(question)

    ranked_number_question = (
        (
            "who was ranked" in question_lower
            or "who is ranked" in question_lower
        )
        and bool(source)
    )

    if ranked_number_question:
        requested_date = None

        if start_date and end_date and start_date == end_date:
            requested_date = start_date
        elif start_date:
            requested_date = start_date

        answer = answer_top_rankings(
            source,
            ranking_type=ranking_type or "singles",
            limit=limit or 1,
            snapshot_date=requested_date,
        )

        return {
            "status": "answered",
            "answer": answer,
        }

    if intent == "player_count":
        return {
            "status": "answered",
            "answer": answer_player_count(),
        }

    if intent == "list_players":
        return {
            "status": "answered",
            "answer": answer_player_list(limit=limit or 10),
        }

    if intent == "top_rankings":
        requested_date = None
        period_start = start_date
        period_end = end_date

        if start_date and end_date and start_date == end_date:
            requested_date = start_date
            period_start = None
            period_end = None
        elif start_date and not end_date:
            requested_date = start_date
            period_start = None

        answer = answer_top_rankings(
            source,
            ranking_type=ranking_type or "singles",
            limit=limit or 5,
            snapshot_date=requested_date,
            start_date=period_start,
            end_date=period_end,
        )

        return {
            "status": "answered",
            "answer": answer,
        }

    if intent == "unknown" and not (
        wants_average or wants_comparison or wants_change
    ):
        return {
            "status": "unsupported",
            "answer": (
                "The requested information is not available "
                "in the structured data."
            ),
        }

    if not player_name:
        return {
            "status": "missing_player",
            "answer": "Please provide a player name.",
        }

    player_result = resolve_player_name(player_name)

    if player_result["status"] == "not_found":
        return {
            "status": "player_not_found",
            "answer": (
                f"I couldn't find a player matching '{player_name}'. "
                f"Please check the name and try again."
            ),
        }

    if player_result["status"] == "ambiguous":
        choices = []

        for player in player_result["players"]:
            description = player["full_name"]

            if player.get("country"):
                description += f" ({player['country']}"

                if player.get("birth_year"):
                    description += f", {player['birth_year']}"

                description += ")"

            elif player.get("birth_year"):
                description += f" ({player['birth_year']})"

            choices.append(description)

        return {
            "status": "ambiguous_player",
            "answer": (
                f"I found multiple players matching '{player_name}':\n"
                + "\n".join(
                    f"{index}. {choice}"
                    for index, choice in enumerate(choices, start=1)
                )
                + "\nPlease provide the full player name."
            ),
        }

    player = player_result["player"]
    player_id = player["player_id"]

    if wants_average:
        answer = answer_average_ranking(
            player,
            source=source,
            ranking_type=ranking_type,
            start_date=start_date,
            end_date=end_date,
        )

    elif wants_comparison:
        answer = answer_period_comparison(
            player,
            source=source,
            ranking_type=ranking_type,
            start_date=start_date,
            end_date=end_date,
            requested_metric=requested_metric or "ranking",
        )

    elif wants_change:
        answer = answer_ranking_change(
            player,
            source=source,
            ranking_type=ranking_type,
            start_date=start_date,
            end_date=end_date,
            requested_metric=requested_metric or "ranking",
        )

    elif intent == "latest_rankings":
        answer = answer_latest_rankings(
            player,
            source=source,
            ranking_type=ranking_type,
            requested_metric=requested_metric,
        )

    elif intent == "ranking_history":
        answer = answer_ranking_history(
            player_id,
            source=source,
            ranking_type=ranking_type,
        )

    elif intent == "filtered_rankings":
        answer = answer_filtered_rankings(
            player,
            source=source,
            ranking_type=ranking_type,
            start_date=start_date,
            end_date=end_date,
        )

    elif intent == "best_ranking":
        answer = answer_best_ranking(
            player,
            source=source,
            ranking_type=ranking_type,
        )

    elif intent == "player_profile":
        answer = answer_player_profile(player, question)

    else:
        return {
            "status": "unsupported",
            "answer": (
                "The requested information is not available "
                "in the structured data."
            ),
        }

    return {
        "status": "answered",
        "answer": answer,
    }
