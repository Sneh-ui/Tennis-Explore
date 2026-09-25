import csv
import glob
import json
import os
import re
from datetime import datetime

import psycopg2


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DATA_ROOT = os.path.expanduser("~/Downloads/ranking-data 5")

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "tennis_rankings_v2",
    "user": "truptimeher",
}


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def get_snapshot_date(filename):
    """
    Extract YYYY-MM-DD from a filename such as:
    atp-2026-01-05.json
    utr-2026-04-27.csv
    """
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)

    if not match:
        return None

    return datetime.strptime(match.group(1), "%Y-%m-%d").date()


def insert_raw_record(cursor, source, file_path, file_name,
                      file_format, snapshot_date, row_number, raw_data):

    cursor.execute(
        """
        INSERT INTO staging.raw_rankings
        (
            source,
            file_path,
            file_name,
            file_format,
            snapshot_date,
            row_number,
            raw_data
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source, file_name, row_number) DO NOTHING
        """,
        (
            source,
            file_path,
            file_name,
            file_format,
            snapshot_date,
            row_number,
            json.dumps(raw_data),
        ),
    )


# --------------------------------------------------
# CSV loader
# --------------------------------------------------

def load_csv_files(cursor, source, pattern):

    files = sorted(glob.glob(os.path.join(DATA_ROOT, pattern)))

    print(f"\n{source.upper()}: found {len(files)} CSV files")

    total_rows = 0

    for file_path in files:

        file_name = os.path.basename(file_path)
        snapshot_date = get_snapshot_date(file_name)

        print(f"  Loading {file_name}...")

        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            file_rows = 0

            for row_number, row in enumerate(reader, start=1):

                insert_raw_record(
                    cursor=cursor,
                    source=source,
                    file_path=file_path,
                    file_name=file_name,
                    file_format="csv",
                    snapshot_date=snapshot_date,
                    row_number=row_number,
                    raw_data=row,
                )

                file_rows += 1
                total_rows += 1

        print(f"    {file_rows:,} rows")

    print(f"{source.upper()} total: {total_rows:,}")

    return total_rows


# --------------------------------------------------
# JSON loader
# --------------------------------------------------

def load_json_files(cursor, source, pattern):

    files = sorted(glob.glob(os.path.join(DATA_ROOT, pattern)))

    print(f"\n{source.upper()}: found {len(files)} JSON files")

    total_rows = 0

    for file_path in files:

        file_name = os.path.basename(file_path)
        snapshot_date = get_snapshot_date(file_name)

        print(f"  Loading {file_name}...")

        # utf-8-sig handles the BOM found in the ATP/WTA files
        with open(
            file_path,
            "r",
            encoding="utf-8-sig"
        ) as file:

            records = json.load(file)

        if not isinstance(records, list):
            raise ValueError(
                f"{file_name} does not contain a JSON list."
            )

        for row_number, record in enumerate(records, start=1):

            insert_raw_record(
                cursor=cursor,
                source=source,
                file_path=file_path,
                file_name=file_name,
                file_format="json",
                snapshot_date=snapshot_date,
                row_number=row_number,
                raw_data=record,
            )

        total_rows += len(records)

        print(f"    {len(records):,} rows")

    print(f"{source.upper()} total: {total_rows:,}")

    return total_rows


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    print("=" * 60)
    print("TENNIS EXPLORE - RAW DATA LOADER")
    print("=" * 60)

    print(f"\nData folder:")
    print(DATA_ROOT)

    connection = psycopg2.connect(**DB_CONFIG)

    try:

        cursor = connection.cursor()

        totals = {}

        # ATP JSON
        totals["ATP"] = load_json_files(
            cursor,
            "ATP",
            "atp/*.json"
        )

        # WTA JSON
        totals["WTA"] = load_json_files(
            cursor,
            "WTA",
            "wta/*.json"
        )

        # ITF CSV
        totals["ITF"] = load_csv_files(
            cursor,
            "ITF",
            "itf/*.csv"
        )

        # UTR CSV
        totals["UTR"] = load_csv_files(
            cursor,
            "UTR",
            "utr/*.csv"
        )

        connection.commit()

        print("\n" + "=" * 60)
        print("LOAD COMPLETE")
        print("=" * 60)

        for source, count in totals.items():
            print(f"{source}: {count:,}")

        print(f"TOTAL: {sum(totals.values()):,}")

    except Exception:

        connection.rollback()
        raise

    finally:

        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
