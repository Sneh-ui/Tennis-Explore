import json
from pathlib import Path

import psycopg2


ATHLETES_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "reference"
    / "tennis_australia_athletes.json"
)

# ------------------------------------------------------------
# Tennis EXPLORE
# Client Athlete Reference Validation
#
# Purpose:
# Compare the Tennis Australia athlete reference list against
# our existing PostgreSQL player identity mappings.
#
# This script is read-only. It does NOT modify the database.
# ------------------------------------------------------------

ATHLETES_FILE = Path.home() / "Downloads" / "athletes.json"


def load_athletes():
    with ATHLETES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_connection():
    return psycopg2.connect(
        dbname="tennis_rankings_v2",
        user="truptimeher",
        port=5433
    )


def get_identifier_match(cur, source, source_player_id):
    if not source_player_id:
        return None

    cur.execute(
        """
        SELECT
            pi.player_id,
            p.full_name,
            p.country,
            p.birth_year
        FROM core.player_identifiers pi
        JOIN core.players p
            ON p.player_id = pi.player_id
        WHERE pi.source = %s
          AND UPPER(pi.source_player_id) = UPPER(%s);
        """,
        (source, str(source_player_id)),
    )

    row = cur.fetchone()

    if not row:
        return None

    return {
        "player_id": row[0],
        "full_name": row[1],
        "country": row[2],
        "birth_year": row[3],
    }


def check_raw_itf(cur, itf_id):
    if not itf_id:
        return False

    cur.execute(
        """
        SELECT 1
        FROM staging.raw_rankings
        WHERE source = 'ITF'
          AND raw_data->>'playerId' = %s
        LIMIT 1;
        """,
        (str(itf_id),),
    )

    return cur.fetchone() is not None


def main():
    athletes = load_athletes()

    print(f"\nClient athletes: {len(athletes)}\n")

    fully_consistent = []
    partially_matched = []
    no_database_match = []
    conflicts = []
    missing_itf_raw = []

    with get_connection() as conn:
        with conn.cursor() as cur:

            for athlete in athletes:

                name = athlete.get("athlete")
                pro_id = athlete.get("pro_id")
                itf_id = athlete.get("itf_id")
                utr_ids = athlete.get("utr_id", [])

                matches = []

                # ------------------------------------------------
                # Pro ID
                # ------------------------------------------------
                if pro_id:
                    source = None

                    if pro_id.upper().startswith("ATP"):
                        source = "ATP"
                    elif pro_id.upper().startswith("WTA"):
                        source = "WTA"

                    if source:
                        result = get_identifier_match(
                            cur,
                            source,
                            pro_id
                        )

                        if result:
                            matches.append(
                                (source, pro_id, result["player_id"])
                            )

                # ------------------------------------------------
                # ITF ID
                # ------------------------------------------------
                if itf_id:
                    result = get_identifier_match(
                        cur,
                        "ITF",
                        str(itf_id)
                    )

                    if result:
                        matches.append(
                            ("ITF", str(itf_id), result["player_id"])
                        )

                    if not check_raw_itf(cur, itf_id):
                        missing_itf_raw.append(
                            {
                                "athlete": name,
                                "itf_id": str(itf_id)
                            }
                        )

                # ------------------------------------------------
                # UTR IDs
                # ------------------------------------------------
                for utr_id in utr_ids:
                    result = get_identifier_match(
                        cur,
                        "UTR",
                        str(utr_id)
                    )

                    if result:
                        matches.append(
                            ("UTR", str(utr_id), result["player_id"])
                        )

                # ------------------------------------------------
                # Classify result
                # ------------------------------------------------

                player_ids = {
                    match[2]
                    for match in matches
                }

                expected_identifiers = 0

                if pro_id:
                    expected_identifiers += 1

                if itf_id:
                    expected_identifiers += 1

                expected_identifiers += len(utr_ids)

                if len(player_ids) > 1:
                    conflicts.append(
                        {
                            "athlete": name,
                            "matches": matches
                        }
                    )

                elif len(matches) == 0:
                    no_database_match.append(
                        {
                            "athlete": name,
                            "pro_id": pro_id,
                            "itf_id": itf_id,
                            "utr_ids": utr_ids
                        }
                    )

                elif len(matches) == expected_identifiers:
                    fully_consistent.append(
                        {
                            "athlete": name,
                            "player_id": next(iter(player_ids)),
                            "matches": matches
                        }
                    )

                else:
                    partially_matched.append(
                        {
                            "athlete": name,
                            "player_id": next(iter(player_ids)),
                            "matches": matches,
                            "pro_id": pro_id,
                            "itf_id": itf_id,
                            "utr_ids": utr_ids
                        }
                    )

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    print("VALIDATION SUMMARY")
    print("------------------")
    print(f"Fully consistent:     {len(fully_consistent)}")
    print(f"Partially matched:    {len(partially_matched)}")
    print(f"No database match:    {len(no_database_match)}")
    print(f"Conflicting mappings: {len(conflicts)}")
    print(f"ITF IDs absent from supplied raw ITF data: {len(missing_itf_raw)}")


    # ------------------------------------------------------------
    # Conflicts
    # ------------------------------------------------------------

    if conflicts:
        print("\nCONFLICTING MAPPINGS")
        print("--------------------")

        for item in conflicts:
            print(f"\n{item['athlete']}")

            for source, identifier, player_id in item["matches"]:
                print(
                    f"  {source} {identifier}"
                    f" -> player_id {player_id}"
                )

    # ------------------------------------------------------------
    # Partial matches
    # ------------------------------------------------------------

    if partially_matched:
        print("\nPARTIALLY MATCHED ATHLETES")
        print("--------------------------")

        for item in partially_matched:
            print(f"\n{item['athlete']}")
            print(f"  Existing player_id: {item['player_id']}")

            for source, identifier, player_id in item["matches"]:
                print(
                    f"  Matched: {source} {identifier}"
                    f" -> player_id {player_id}"
                )

            print(f"  Client Pro ID: {item['pro_id']}")
            print(f"  Client ITF ID: {item['itf_id']}")
            print(f"  Client UTR IDs: {item['utr_ids']}")

    # ------------------------------------------------------------
    # No matches
    # ------------------------------------------------------------

    if no_database_match:
        print("\nNO DATABASE MATCH")
        print("-----------------")

        for item in no_database_match:
            print(
                f"{item['athlete']} | "
                f"Pro={item['pro_id']} | "
                f"ITF={item['itf_id']} | "
                f"UTR={item['utr_ids']}"
            )

    # ------------------------------------------------------------
    # ITF IDs missing from supplied raw ITF dataset
    # ------------------------------------------------------------

    if missing_itf_raw:
        print("\nCLIENT ITF IDs NOT PRESENT IN SUPPLIED ITF RANKING DATA")
        print("-------------------------------------------------------")

        for item in missing_itf_raw:
            print(
                f"{item['athlete']} -> ITF {item['itf_id']}"
            )


if __name__ == "__main__":
    main()
