import argparse
import csv
import json
import os
from pathlib import Path

import psycopg


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

MANIFEST_PATH = (
    BASE_DIR
    / "outputs"
    / "production"
    / "processing_manifest.csv"
)

CHUNKS_DIR = (
    BASE_DIR
    / "outputs"
    / "production"
    / "chunks"
)


# ============================================================
# Database configuration
# ============================================================

def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "tennis_rankings"),
        "user": os.getenv("DB_USER", os.getenv("USER", "")),
        "password": os.getenv("DB_PASSWORD") or None,
    }


# ============================================================
# Document helpers
# ============================================================

def mb_to_bytes(value):
    if value is None or str(value).strip() == "":
        return None

    try:
        return int(float(value) * 1024 * 1024)
    except (TypeError, ValueError):
        return None


def build_document_record(row):
    extraction_status = (
        row.get("extraction_status") or ""
    ).strip()

    return {
        "resource_id": (row.get("resource_id") or "").strip(),
        "source_system": "aws_s3",
        "source_location": (row.get("s3_key") or "").strip(),
        "file_name": (row.get("file_name") or "").strip(),
        "file_type": (row.get("file_type") or "").strip().lower(),
        "size_bytes": mb_to_bytes(row.get("size_mb")),
        "etag": (row.get("etag") or "").strip() or None,
        "last_modified": (
            row.get("last_modified") or ""
        ).strip() or None,
        "processing_status": (
            row.get("processing_status") or ""
        ).strip() or None,
        "extraction_status": extraction_status or None,
        "chunking_status": (
            row.get("chunking_status") or ""
        ).strip() or None,
        "chunk_count": int(row.get("chunk_count") or 0),
        "processed_at": (
            row.get("processed_at") or ""
        ).strip() or None,
        "requires_ocr": extraction_status == "needs_ocr",
        "error_type": (
            row.get("error_type") or ""
        ).strip() or None,
        "error_message": (
            row.get("error_message") or ""
        ).strip() or None,
    }


def load_manifest():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}"
        )

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    return [build_document_record(row) for row in rows]


# ============================================================
# Document SQL
# ============================================================

INSERT_DOCUMENT_SQL = """
INSERT INTO unstructured.documents (
    resource_id,
    source_system,
    source_location,
    file_name,
    file_type,
    size_bytes,
    etag,
    last_modified,
    processing_status,
    extraction_status,
    chunking_status,
    chunk_count,
    processed_at,
    requires_ocr,
    error_type,
    error_message
)
VALUES (
    %(resource_id)s,
    %(source_system)s,
    %(source_location)s,
    %(file_name)s,
    %(file_type)s,
    %(size_bytes)s,
    %(etag)s,
    %(last_modified)s,
    %(processing_status)s,
    %(extraction_status)s,
    %(chunking_status)s,
    %(chunk_count)s,
    %(processed_at)s,
    %(requires_ocr)s,
    %(error_type)s,
    %(error_message)s
)
ON CONFLICT (resource_id)
DO UPDATE SET
    source_system = EXCLUDED.source_system,
    source_location = EXCLUDED.source_location,
    file_name = EXCLUDED.file_name,
    file_type = EXCLUDED.file_type,
    size_bytes = EXCLUDED.size_bytes,
    etag = EXCLUDED.etag,
    last_modified = EXCLUDED.last_modified,
    processing_status = EXCLUDED.processing_status,
    extraction_status = EXCLUDED.extraction_status,
    chunking_status = EXCLUDED.chunking_status,
    chunk_count = EXCLUDED.chunk_count,
    processed_at = EXCLUDED.processed_at,
    requires_ocr = EXCLUDED.requires_ocr,
    error_type = EXCLUDED.error_type,
    error_message = EXCLUDED.error_message,
    updated_at = CURRENT_TIMESTAMP;
"""


# ============================================================
# Chunk SQL
# ============================================================

INSERT_CHUNK_SQL = """
INSERT INTO unstructured.document_chunks (
    document_id,
    source_chunk_id,
    chunk_index,
    page_number,
    slide_number,
    chunk_text,
    word_count,
    character_count
)
VALUES (
    %(document_id)s,
    %(source_chunk_id)s,
    %(chunk_index)s,
    %(page_number)s,
    %(slide_number)s,
    %(chunk_text)s,
    %(word_count)s,
    %(character_count)s
)
ON CONFLICT (document_id, source_chunk_id)
DO UPDATE SET
    chunk_index = EXCLUDED.chunk_index,
    page_number = EXCLUDED.page_number,
    slide_number = EXCLUDED.slide_number,
    chunk_text = EXCLUDED.chunk_text,
    word_count = EXCLUDED.word_count,
    character_count = EXCLUDED.character_count;
"""


# ============================================================
# Document loading
# ============================================================

def load_documents(records):
    config = get_db_config()

    print("=" * 70)
    print("TENNIS EXPLORE - POSTGRES DOCUMENT LOADER")
    print("=" * 70)

    print(f"\nDatabase : {config['dbname']}")
    print(f"Host     : {config['host']}")
    print(f"Port     : {config['port']}")
    print(f"User     : {config['user']}")

    print(f"\nDocument records ready : {len(records)}")

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT current_database(),
                       current_setting('server_version');
                """
            )

            database_name, version = cur.fetchone()

            print(f"Connected database      : {database_name}")
            print(f"PostgreSQL version      : {version}")

            print("\nLoading document records...")

            for record in records:
                cur.execute(INSERT_DOCUMENT_SQL, record)

    print(f"Loaded/upserted          : {len(records)}")
    print("\nDocument loading complete.")
    print("=" * 70)


# ============================================================
# Document ID mapping
# ============================================================

def get_document_id_map(cur):
    cur.execute(
        """
        SELECT resource_id, document_id
        FROM unstructured.documents;
        """
    )

    return {
        resource_id: document_id
        for resource_id, document_id in cur.fetchall()
    }


# ============================================================
# Chunk helpers
# ============================================================

def clean_postgres_text(value):
    """
    Remove NUL characters because PostgreSQL TEXT fields
    cannot contain the \\x00 character.
    """
    if value is None:
        return None

    return str(value).replace("\x00", "")


def build_chunk_record(document_id, chunk):
    cleaned_text = clean_postgres_text(chunk["text"])
    cleaned_chunk_id = clean_postgres_text(chunk["chunk_id"])

    return {
        "document_id": document_id,
        "source_chunk_id": cleaned_chunk_id,
        "chunk_index": int(chunk["chunk_index"]),
        "page_number": chunk.get("page_number"),
        "slide_number": chunk.get("slide_number"),
        "chunk_text": cleaned_text,
        "word_count": chunk.get("word_count"),
        "character_count": len(cleaned_text),
    }


def get_chunk_files():
    if not CHUNKS_DIR.exists():
        raise FileNotFoundError(
            f"Chunk directory not found: {CHUNKS_DIR}"
        )

    return sorted(CHUNKS_DIR.glob("*.json"))


# ============================================================
# Chunk dry run
# ============================================================

def chunk_dry_run():
    files = get_chunk_files()

    total_chunks = 0
    valid_files = 0
    errors = []

    for path in files:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            output_stem = data.get("output_stem", "")

            if "_" not in output_stem:
                raise ValueError(
                    "Invalid or missing output_stem"
                )

            resource_id = output_stem.split("_", 1)[0]

            chunks = data.get("chunks", [])

            for chunk in chunks:
                if not chunk.get("chunk_id"):
                    raise ValueError("Missing chunk_id")

                if "chunk_index" not in chunk:
                    raise ValueError("Missing chunk_index")

                if not chunk.get("text"):
                    raise ValueError("Missing chunk text")

            total_chunks += len(chunks)
            valid_files += 1

        except Exception as exc:
            errors.append(
                f"{path.name}: {type(exc).__name__}: {exc}"
            )

    print("=" * 70)
    print("TENNIS EXPLORE - CHUNK DATABASE DRY RUN")
    print("=" * 70)

    print(f"\nChunk JSON files : {len(files)}")
    print(f"Valid files      : {valid_files}")
    print(f"Total chunks     : {total_chunks}")
    print(f"Errors           : {len(errors)}")

    if errors:
        print("\nErrors:")
        for error in errors[:20]:
            print(f"  {error}")

    print("\nNO DATABASE CHANGES MADE.")
    print("=" * 70)


# ============================================================
# Chunk loading
# ============================================================

def load_chunks():
    config = get_db_config()
    files = get_chunk_files()

    print("=" * 70)
    print("TENNIS EXPLORE - POSTGRES CHUNK LOADER")
    print("=" * 70)

    print(f"\nDatabase         : {config['dbname']}")
    print(f"Chunk JSON files : {len(files)}")

    files_processed = 0
    chunks_processed = 0

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:

            document_map = get_document_id_map(cur)

            print(
                f"Document mappings: {len(document_map)}"
            )

            for file_number, path in enumerate(files, start=1):

                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                output_stem = data.get("output_stem", "")

                if "_" not in output_stem:
                    raise RuntimeError(
                        f"Cannot derive resource_id from "
                        f"{path.name}"
                    )

                resource_id = output_stem.split("_", 1)[0]

                document_id = document_map.get(resource_id)

                if document_id is None:
                    raise RuntimeError(
                        f"No PostgreSQL document found for "
                        f"resource_id={resource_id} "
                        f"({path.name})"
                    )

                chunks = data.get("chunks", [])

                records = [
                    build_chunk_record(document_id, chunk)
                    for chunk in chunks
                ]

                if records:
                    cur.executemany(
                        INSERT_CHUNK_SQL,
                        records,
                    )

                files_processed += 1
                chunks_processed += len(records)

                # Commit after each source document.
                # This makes the load resumable.
                conn.commit()

                if (
                    file_number % 100 == 0
                    or file_number == len(files)
                ):
                    print(
                        f"Processed files : "
                        f"{file_number}/{len(files)} | "
                        f"Chunks : {chunks_processed}"
                    )

    print("\n" + "=" * 70)
    print("CHUNK LOADING COMPLETE")
    print("=" * 70)

    print(f"Files processed : {files_processed}")
    print(f"Chunks processed: {chunks_processed}")


# ============================================================
# Document dry run
# ============================================================

def document_dry_run(records):
    config = get_db_config()

    print("=" * 70)
    print("TENNIS EXPLORE - POSTGRES LOAD DRY RUN")
    print("=" * 70)

    print(f"\nDatabase : {config['dbname']}")
    print(f"Host     : {config['host']}")
    print(f"Port     : {config['port']}")
    print(f"User     : {config['user']}")

    print(
        f"\nDocuments that would be loaded : "
        f"{len(records)}"
    )

    if records:
        print("\nSample record:")

        for key, value in records[0].items():
            print(f"{key:<20}: {value}")

    print("\nNO DATABASE CHANGES MADE.")
    print("=" * 70)


# ============================================================
# Entry point
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run for document records.",
    )

    parser.add_argument(
        "--load-documents",
        action="store_true",
        help="Load/upsert document records.",
    )

    parser.add_argument(
        "--chunk-dry-run",
        action="store_true",
        help="Validate chunk files before database loading.",
    )

    parser.add_argument(
        "--load-chunks",
        action="store_true",
        help="Load/upsert chunks into PostgreSQL.",
    )

    args = parser.parse_args()

    selected = sum(
        [
            args.dry_run,
            args.load_documents,
            args.chunk_dry_run,
            args.load_chunks,
        ]
    )

    if selected != 1:
        parser.error(
            "Choose exactly one operation: "
            "--dry-run, --load-documents, "
            "--chunk-dry-run, or --load-chunks"
        )

    if args.chunk_dry_run:
        chunk_dry_run()
        return

    if args.load_chunks:
        load_chunks()
        return

    records = load_manifest()

    if args.dry_run:
        document_dry_run(records)
        return

    if args.load_documents:
        load_documents(records)


if __name__ == "__main__":
    main()