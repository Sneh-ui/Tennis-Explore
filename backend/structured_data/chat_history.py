from backend.structured_data.database import get_db_connection


def save_chat_history(user_id: int, question: str, answer: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_chat.chat_history (user_id, question, answer)
                VALUES (%s, %s, %s)
                RETURNING id, user_id, question, answer, created_at
                """,
                (user_id, question, answer),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        conn.close()


def get_chat_history(user_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, question, answer, created_at
                FROM app_chat.chat_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
