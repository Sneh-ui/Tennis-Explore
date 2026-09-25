import json
from pathlib import Path

import psycopg2


# ------------------------------------------------------------
# Tennis EXPLORE
# Tennis Australia Athlete Reference Loader
#
# Loads the curated athlete reference supplied directly by
# Tennis Australia into core.ta_athletes.
#
# This data provides athlete identity information and trusted
# cross-organisation identifiers.
# ------------------------------------------------------------

ATHLETES_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "reference"
    / "tennis_australia_athletes.json"
)


def get_connection():
    return psycopg2.connect(
        dbname="tennis_rankings_v2",
        user="truptimeher",
        port=5433
    )


def load_athletes():
    with ATHLETES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    athletes = load_athletes()

    print(f"TA athlete records found: {len(athletes)}")

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Create the reference table if it does not already exist.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS core.ta_athletes (
                    ta_athlete_id BIGSERIAL PRIMARY KEY,
                    athlete_name TEXT NOT NULL,
                    dob DATE,
                    state TEXT,
                    program TEXT,
                    pro_id TEXT,
                    itf_id TEXT,
                    utr_ids TEXT[],
                    tennis_id TEXT,
                    aus_id TEXT,
                    lmid TEXT,
                    tcid TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                ALTER TABLE core.ta_athletes
                    ADD COLUMN IF NOT EXISTS tennis_id TEXT,
                    ADD COLUMN IF NOT EXISTS aus_id TEXT,
                    ADD COLUMN IF NOT EXISTS lmid TEXT,
                    ADD COLUMN IF NOT EXISTS tcid TEXT;
                """
            )
            # Reload from the project reference file so repeated
            # executions do not create duplicate reference records.
            cur.execute("TRUNCATE TABLE core.ta_athletes RESTART IDENTITY;")

            for athlete in athletes:
                cur.execute(
                    """
                    INSERT INTO core.ta_athletes (
                        athlete_name,
                        dob,
                        state,
                        program,
                        pro_id,
                        itf_id,
                        utr_ids,
                        tennis_id,
                        aus_id,
                        lmid,
                        tcid
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    
                    
                     """,
                    (
                        athlete.get("athlete"),
                        athlete.get("dob"),
                        athlete.get("state"),
                        athlete.get("program"),
                        athlete.get("pro_id"),
                        (
                            str(athlete.get("itf_id"))
                            if athlete.get("itf_id") is not None
                            else None
                        ),
                        [
                            str(utr_id)
                            for utr_id in athlete.get("utr_id", [])
                        ],
                        athlete.get("tennis_id"),
                        athlete.get("aus_id"),
                        athlete.get("lmid"),
                        athlete.get("tcid"),
                    ),
                )

    print("TA athlete reference loaded successfully.")
    print("No core player identities were changed.")


if __name__ == "__main__":
    main()

