import json

import requests

from backend.structured_data.queries import (
    search_players,
    fuzzy_search_players,
    get_player_ranking_history,
    get_latest_player_rankings,
    get_filtered_player_rankings,
    get_best_player_ranking,
    get_top_ranked_players,
    get_player_profile,
    get_latest_filtered_player_rankings,
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
        if source:
            heading = f"{name}'s latest available {source.upper()} rankings:"
        else:
            heading = f"{name}'s latest available rankings:"

    elif requested_metric == "rating":
        if source:
            heading = f"{name}'s latest available {source.upper()} ratings:"
        else:
            heading = f"{name}'s latest available ratings:"

    else:
        if source:
            heading = f"{name}'s latest available {source.upper()} ranking and rating data:"
        else:
            heading = f"{name}'s latest available ranking and rating data:"
    return heading + "\n" + "\n".join(lines)
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
            return f"{requested} ranking or rating history is not available for this player."

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
                values.append(
                    f"{format_number(row['points'])} points"
                )

            if row["rating"] is not None:
                values.append(
                    f"rating {format_number(row['rating'])}"
                )

            if values:
                lines.append(
                    f"- {format_date(row['snapshot_date'])}: "
                    + ", ".join(values)
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
        if best_score >= 0.60 and best_score - second_score >= 0.10:
            return {
                "status": "matched",
                "player": best,
                "match_type": "fuzzy",
            }

        # If even the best fuzzy result is weak, this is not
        # a meaningful player match.
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
    prompt = f"""
You are a routing assistant for Tennis EXPLORE.

Your job is ONLY to understand a structured tennis-data question.

Extract:
1. intent
2. exact player-name text if present
3. source if mentioned
4. ranking type if mentioned
5. start date if clearly requested
6. end date if clearly requested
7. requested top-N limit if applicable

IMPORTANT:
- Copy the player name exactly as entered.
- Never correct or invent a player name.
- Never invent dates.
- Never invent missing information.
- Do not answer the tennis question.
- Do not generate SQL.
- Database values will be retrieved separately.

Supported sources:
ATP
WTA
ITF
UTR

Supported ranking types:
singles
doubles

Only return "singles" or "doubles" when the user explicitly states it.
If the user asks for UTR rating without saying singles or doubles,
ranking_type MUST be null. Do not assume singles.

Allowed intents:
- latest_rankings
- ranking_history
- filtered_rankings
- best_ranking
- top_rankings
- player_profile
- unknown

Use "latest_rankings" for the latest/current/most recent
ranking or rating of a player.

Use "ranking_history" for a player's overall ranking or
rating history or changes over time when no specific
source/date filter is requested.

Use "filtered_rankings" when the user asks for ranking or
rating information for a particular source, ranking type,
date, month, year, or date range.

Use "best_ranking" when the user asks for the player's best,
highest, peak, or career-best numerical ranking.

Use "top_rankings" when the user asks who the top-ranked
players are, for example top 5 ATP singles players.

Use "player_profile" for basic player information such as
country, gender, or birth year.

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
- If no date is requested, use null.
- Do not guess an unspecified date.

For top-N questions:
- Return the requested number as "limit".
- If the user says "top players" without a number, use 5.
- Otherwise use null when this is not a top-ranking question.

Return ONLY valid JSON with exactly these keys:
{{
  "intent": "...",
  "player_name": null,
  "source": null,
  "ranking_type": null,
  "start_date": null,
  "end_date": null,
  "limit": null
}}

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
            "source": None,
            "ranking_type": None,
            "start_date": None,
            "end_date": None,
            "limit": None,
        }
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

    # If a period contains multiple records, return the records
    # rather than pretending there was only one value.
    lines = []

    for row in rows:
        value = describe_record(row)

        if value:
            lines.append(
                f"- {format_date(row['snapshot_date'])}: "
                f"{row['source']} {row['ranking_type'].title()} — {value}"
            )

    if not lines:
        return f"The requested ranking or rating information is not available for {name}."

    if start_date and end_date:
        if start_date == end_date:
            period = f"on {format_date(start_date)}"
        else:
            period = f"from {format_date(start_date)} to {format_date(end_date)}"

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
            f"{name}'s available {source.upper()} data "
            f"{period}:"
        )

    else:
        heading = (
            f"{name}'s available ranking and rating data "
            f"{period}:"
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
    """
    Compare the earliest and latest available values in a requested period.

    For ranking, a lower numerical rank is better.
    For rating, a higher numerical rating is higher.
    """
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
            change_text = f"improved by {format_number(abs(difference))} positions"
        elif difference < 0:
            change_text = f"declined by {format_number(abs(difference))} positions"
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
    """
    Calculate the arithmetic mean of available ranking snapshots
    in an explicitly requested period.
    """
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

    # Do not mix different ranking organisations/types in one average.
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
    """
    Compare the last available value in the first requested period
    with the last available value in the second requested period.

    The router currently represents a multi-month request as one
    start/end range, so we compare the last snapshot in the start
    month with the last snapshot in the end month.
    """
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
            change = f"an improvement of {format_number(difference)} positions"
        elif difference < 0:
            change = f"a decline of {format_number(abs(difference))} positions"
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

def answer_top_rankings(
    source,
    ranking_type="singles",
    limit=5,
    snapshot_date=None,
):
    if not source:
        return "Please specify a ranking organisation such as ATP, WTA or ITF."

    rows = get_top_ranked_players(
        source,
        ranking_type=ranking_type or "singles",
        snapshot_date=snapshot_date,
        limit=limit or 5,
    )

    if not rows:
        if snapshot_date:
            return (
                f"{source.upper()} {(ranking_type or 'singles').lower()} "
                f"ranking data is not available on "
                f"{format_date(snapshot_date)}."
            )

        return (
            f"{source.upper()} {(ranking_type or 'singles').lower()} "
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

        if snapshot_date:
            return (
                f"{row['full_name']}{country} was ranked number "
                f"{row['rank']} in {source.upper()} "
                f"{(ranking_type or 'singles').lower()} on "
                f"{actual_date}."
            )

        return (
            f"{row['full_name']}{country} is ranked number "
            f"{row['rank']} in the latest {source.upper()} "
            f"{(ranking_type or 'singles').lower()} ranking "
            f"available in the database ({actual_date})."
        )
    if snapshot_date:
        intro = (
            f"In the {source.upper()} "
            f"{(ranking_type or 'singles').lower()} ranking "
            f"on {actual_date}, the top {len(rows)} players are:"
        )
    else:
        intro = (
            f"In the latest {source.upper()} "
            f"{(ranking_type or 'singles').lower()} ranking available "
            f"in the database ({actual_date}), "
            f"the top {len(rows)} players are:"
        )

    lines = [intro]

    for row in rows:
        country = (
            f" ({format_country(row['country'])})"
            if row.get("country")
            else ""
        )

        lines.append(
            f"{row['rank']}. {row['full_name']}{country}"
        )

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

    return f"Additional profile information is not available for {name}."
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
def answer_structured_question(question):
    understood = understand_question(question)

    intent = understood.get("intent")
    player_name = understood.get("player_name")
    source = understood.get("source")
    ranking_type = understood.get("ranking_type")
    start_date = understood.get("start_date")
    end_date = understood.get("end_date")
    limit = understood.get("limit")
    # A question using "on <date>" means an exact snapshot date.
    # The router may return only start_date, so make the range exact.
    if (
        start_date
        and not end_date
        and " on " in f" {question.lower()} "
    ):
        end_date = start_date
    question_lower = question.lower()
    requested_metric = None
    wants_average = "average" in question_lower

    wants_comparison = (
        "compare" in question_lower
        or "compared" in question_lower
        or "comparison" in question_lower
    )

    wants_change = (
        "improved" in question_lower
        or "improve" in question_lower
        or "declined" in question_lower
        or "decline" in question_lower
        or "changed" in question_lower
        or "change" in question_lower
        or "increased" in question_lower
        or "increase" in question_lower
        or "decreased" in question_lower
        or "decrease" in question_lower
    )

    if "rating" in question_lower:
        requested_metric = "rating"
    elif "ranking" in question_lower or "rank" in question_lower:
        requested_metric = "ranking"
    unsupported_terms = {
        "ace": "Aces",
        "aces": "Aces",
        "double fault": "Double-fault",
        "double faults": "Double-fault",
        "winner": "Winner",
        "winners": "Winner",
        "unforced error": "Unforced-error",
        "unforced errors": "Unforced-error",
        "serve percentage": "Serve-percentage",
        "break point": "Break-point",
        "break points": "Break-point",
        "matches won": "Match win/loss",
        "matches did": "Match win/loss",
        "match wins": "Match win/loss",
        "wins": "Match win/loss",
        "losses": "Match win/loss",
        "win loss": "Match win/loss",
        "win/loss": "Match win/loss",
    }

    for term, label in unsupported_terms.items():
        if term in question_lower:
            return {
                "status": "unsupported",
                "answer": f"{label} information is not available in the structured data.",
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
    # Questions such as:
    # "Who was ranked number 1 in ATP singles on 2 March 2026?"
    ranked_number_question = (
        ("who was ranked" in question_lower or "who is ranked" in question_lower)
        and source
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

    if intent == "unknown" and not (
        wants_average
        or wants_comparison
        or wants_change
    ):
        return {
            "status": "unsupported",
            "answer": "The requested information is not available in the structured data.",
        }

    if intent == "top_rankings":
        requested_date = None

        if start_date and end_date and start_date == end_date:
            requested_date = start_date
        elif start_date and not end_date:
            requested_date = start_date

        answer = answer_top_rankings(
            source,
            ranking_type=ranking_type or "singles",
            limit=limit or 5,
            snapshot_date=requested_date,
        )

        return {
            "status": "answered",
            "answer": answer,
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
                f"I found multiple players matching '{player_name}': "
                + ", ".join(choices)
                + ". Please provide the full player name."
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

        return {
            "status": "answered",
            "answer": answer,
        }

    if wants_comparison:
        answer = answer_period_comparison(
            player,
            source=source,
            ranking_type=ranking_type,
            start_date=start_date,
            end_date=end_date,
            requested_metric=requested_metric or "ranking",
        )

        return {
            "status": "answered",
            "answer": answer,
        }

    if wants_change:
        answer = answer_ranking_change(
            player,
            source=source,
            ranking_type=ranking_type,
            start_date=start_date,
            end_date=end_date,
            requested_metric=requested_metric or "ranking",
        )

        return {
            "status": "answered",
            "answer": answer,
        }
    if intent == "latest_rankings":
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
        answer = "The requested information is not available in the structured data."

    return {
        "status": "answered",
        "answer": answer,
    }
