from backend.structured_data.database import get_db_connection


def search_players(name, limit=10):
    """
    Search master players by name.
    """
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    player_id,
                    full_name,
                    country,
                    birth_year
                FROM core.players
                WHERE full_name ILIKE %s
                ORDER BY full_name
                LIMIT %s;
                """,
                (f"%{name}%", limit),
            )

            return [dict(row) for row in cur.fetchall()]

    finally:
        conn.close()


def get_player_ranking_history(player_id):
    """
    Return all available ranking/rating history for one master player.
    """
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    source,
                    ranking_type,
                    rank,
                    points,
                    rating,
                    snapshot_date
                FROM core.ranking_snapshots
                WHERE player_id = %s
                ORDER BY snapshot_date, source, ranking_type;
                """,
                (player_id,),
            )

            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_latest_player_rankings(player_id):
    """
    Return the latest available record for each source and ranking type.
    """
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (source, ranking_type)
                    source,
                    ranking_type,
                    rank,
                    points,
                    rating,
                    snapshot_date
                FROM core.ranking_snapshots
                WHERE player_id = %s
                ORDER BY
                    source,
                    ranking_type,
                    snapshot_date DESC,
                    ranking_id DESC;
                """,
                (player_id,),
            )

            return [dict(row) for row in cur.fetchall()]

    finally:
        conn.close()
def fuzzy_search_players(name, limit=5):
    """
    Find the closest player-name matches across the full player table.
    The limit controls only how many best matches are returned.
    """
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    player_id,
                    full_name,
                    country,
                    birth_year,
                    similarity(full_name, %s) AS similarity_score
                FROM core.players
                WHERE full_name IS NOT NULL
                  AND TRIM(full_name) <> ''
                ORDER BY
                    similarity(full_name, %s) DESC NULLS LAST
                LIMIT %s;
                """,
                (name, name, limit),
            )

            return [dict(row) for row in cur.fetchall()]

    finally:
        conn.close()
def get_filtered_player_rankings(
    player_id,
    source=None,
    ranking_type=None,
    start_date=None,
    end_date=None,
):
    """
    Return ranking/rating records for a player with optional
    source, ranking type, and date filters.
    """
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            conditions = ["player_id = %s"]
            params = [player_id]

            if source:
                conditions.append("UPPER(source) = UPPER(%s)")
                params.append(source)

            if ranking_type:
                conditions.append("LOWER(ranking_type) = LOWER(%s)")
                params.append(ranking_type)

            if start_date:
                conditions.append("snapshot_date >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("snapshot_date <= %s")
                params.append(end_date)

            query = f"""
                SELECT
                    source,
                    ranking_type,
                    rank,
                    points,
                    rating,
                    snapshot_date
                FROM core.ranking_snapshots
                WHERE {" AND ".join(conditions)}
                ORDER BY snapshot_date, source, ranking_type;
            """

            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    finally:
        conn.close()


def get_best_player_ranking(player_id, source=None, ranking_type=None):
    """
    Return the best (lowest numerical) ranking achieved by a player.
    """
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            conditions = [
                "player_id = %s",
                "rank IS NOT NULL",
            ]
            params = [player_id]

            if source:
                conditions.append("UPPER(source) = UPPER(%s)")
                params.append(source)

            if ranking_type:
                conditions.append("LOWER(ranking_type) = LOWER(%s)")
                params.append(ranking_type)

            query = f"""
                SELECT
                    source,
                    ranking_type,
                    rank,
                    points,
                    rating,
                    snapshot_date
                FROM core.ranking_snapshots
                WHERE {" AND ".join(conditions)}
                ORDER BY rank ASC, snapshot_date DESC
                LIMIT 1;
            """

            cur.execute(query, params)
            row = cur.fetchone()

            return dict(row) if row else None

    finally:
        conn.close()


def get_top_ranked_players(
    source,
    ranking_type="singles",
    snapshot_date=None,
    limit=5,
):
    """
    Return top-ranked players for a source and ranking type.

    If no date is supplied, use the latest available date
    for that source and ranking type.
    """
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            if snapshot_date is None:
                cur.execute(
                    """
                    SELECT MAX(snapshot_date)
                    FROM core.ranking_snapshots
                    WHERE UPPER(source) = UPPER(%s)
                      AND LOWER(ranking_type) = LOWER(%s)
                      AND rank IS NOT NULL;
                    """,
                    (source, ranking_type),
                )

                result = cur.fetchone()

                if not result or result["max"] is None:
                    return []

                snapshot_date = result["max"]

            cur.execute(
                """
                SELECT
                    p.player_id,
                    p.full_name,
                    p.country,
                    r.source,
                    r.ranking_type,
                    r.rank,
                    r.points,
                    r.rating,
                    r.snapshot_date
                FROM core.ranking_snapshots r
                JOIN core.players p
                    ON p.player_id = r.player_id
                WHERE UPPER(r.source) = UPPER(%s)
                  AND LOWER(r.ranking_type) = LOWER(%s)
                  AND r.snapshot_date = %s
                  AND r.rank IS NOT NULL
                ORDER BY r.rank ASC
                LIMIT %s;
                """,
                (source, ranking_type, snapshot_date, limit),
            )

            return [dict(row) for row in cur.fetchall()]

    finally:
        conn.close()


def get_player_profile(player_id):
    """
    Return basic master-player information.
    """
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    player_id,
                    full_name,
                    first_name,
                    last_name,
                    gender,
                    country,
                    birth_year
                FROM core.players
                WHERE player_id = %s;
                """,
                (player_id,),
            )

            row = cur.fetchone()
            return dict(row) if row else None

    finally:
        conn.close()
def get_latest_filtered_player_rankings(
    player_id,
    source=None,
    ranking_type=None,
):
    """
    Return the latest available ranking/rating records for a player,
    optionally filtered by organisation and ranking type.
    """
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            conditions = ["player_id = %s"]
            params = [player_id]

            if source:
                conditions.append("UPPER(source) = UPPER(%s)")
                params.append(source)

            if ranking_type:
                conditions.append("LOWER(ranking_type) = LOWER(%s)")
                params.append(ranking_type)

            query = f"""
                SELECT DISTINCT ON (source, ranking_type)
                    source,
                    ranking_type,
                    rank,
                    points,
                    rating,
                    snapshot_date
                FROM core.ranking_snapshots
                WHERE {" AND ".join(conditions)}
                ORDER BY
                    source,
                    ranking_type,
                    snapshot_date DESC,
                    ranking_id DESC;
            """

            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    finally:
        conn.close()
