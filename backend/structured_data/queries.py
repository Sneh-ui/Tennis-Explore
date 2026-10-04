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
