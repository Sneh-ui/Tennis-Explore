import os

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """
    Create a PostgreSQL connection for the structured tennis database.

    Connection settings are read from environment variables so local
    credentials are never stored in Git.
    """
    return psycopg2.connect(
        host=os.getenv("STRUCTURED_DB_HOST", "localhost"),
        port=os.getenv("STRUCTURED_DB_PORT", "5433"),
        dbname=os.getenv("STRUCTURED_DB_NAME", "tennis_rankings_v2"),
        user=os.getenv("STRUCTURED_DB_USER"),
        password=os.getenv("STRUCTURED_DB_PASSWORD"),
        cursor_factory=RealDictCursor,
    )

