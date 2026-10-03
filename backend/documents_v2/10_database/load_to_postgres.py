import argparse
import csv
import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


load_dotenv()


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
        "dbname": os.getenv(
            "DB_NAME",
            "tennis_rankings",
        ),
        "user": os.getenv(
            "DB_USER",
            os.getenv("USER", ""),
        ),
        "password": (
            os.getenv("DB_PASSWORD") or None
        ),
    }


# ============================================================
# Document helpers
# ============================================================

def mb_to_bytes(value):
    if value is None or str(value).strip() == "":
        return None

    try:
        return int(
            float(value) * 1024 * 1024
        )
    except (TypeError, ValueError):
        return None


def build_document_record(row):
    extraction_status = (
        row.get("extraction_status") or ""
    ).strip()

    return {
        "resource_id": (
            row.get("resource_id") or ""
        ).strip(),

        "source_system": "aws_s3",

        "source_location": (
            row.get("s3_key") or ""
        ).strip(),

        "file_name": (
            row.get("file_name") or ""
        ).strip(),

        "file_type": (
            row.get("file_type") or ""
        ).strip().lower(),

        "size_bytes": mb_to_bytes(
            row.get("size_mb")
        ),

        "etag": (
            row.get("etag") or ""
        ).strip() or None,

        "last_modified": (
            row.get("last_modified") or ""
        ).strip() or None,

        "processing_status": (
            row.get("processing_status") or ""
        ).strip() or None,

        "extraction_status":
            extraction_status or None,

        "chunking_status": (
            row.get("chunking_status") or ""
        ).strip() or None,

        "chunk_count": int(
            row.get("chunk_count") or 0
        ),

        "processed_at": (
            row.get("processed_at") or ""
        ).strip() or None,

        "requires_ocr":
            extraction_status == "needs_ocr",

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
            f"Manifest not found: "
            f"{MANIFEST_PATH}"
        )

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    return [
        build_document_record(row)
        for row in rows
    ]


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
    print(
        "TENNIS EXPLORE - "
        "POSTGRES DOCUMENT LOADER"
    )
    print("=" * 70)

    print(
        f"\nDatabase : {config['dbname']}"
    )
    print(
        f"Host     : {config['host']}"
    )
    print(
        f"Port     : {config['port']}"
    )
    print(
        f"User     : {config['user']}"
    )

    print(
        f"\nDocument records ready : "
        f"{len(records)}"
    )

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    current_database(),
                    current_setting(
                        'server_version'
                    );
                """
            )

            database_name, version = (
                cur.fetchone()
            )

            print(
                f"Connected database      : "
                f"{database_name}"
            )

            print(
                f"PostgreSQL version      : "
                f"{version}"
            )

            print(
                "\nLoading document records..."
            )

            for record in records:
                cur.execute(
                    INSERT_DOCUMENT_SQL,
                    record,
                )

    print(
        f"Loaded/upserted          : "
        f"{len(records)}"
    )

    print(
        "\nDocument loading complete."
    )

    print("=" * 70)


# ============================================================
# Document ID mapping
# ============================================================

def get_document_id_map(cur):
    cur.execute(
        """
        SELECT
            resource_id,
            document_id
        FROM unstructured.documents;
        """
    )

    return {
        resource_id: document_id
        for resource_id, document_id
        in cur.fetchall()
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

    return str(value).replace(
        "\x00",
        "",
    )


def build_chunk_record(
    document_id,
    chunk,
):
    cleaned_text = clean_postgres_text(
        chunk["text"]
    )

    cleaned_chunk_id = (
        clean_postgres_text(
            chunk["chunk_id"]
        )
    )

    return {
        "document_id":
            document_id,

        "source_chunk_id":
            cleaned_chunk_id,

        "chunk_index":
            int(chunk["chunk_index"]),

        "page_number":
            chunk.get("page_number"),

        "slide_number":
            chunk.get("slide_number"),

        "chunk_text":
            cleaned_text,

        "word_count":
            chunk.get("word_count"),

        "character_count":
            len(cleaned_text),
    }


def get_chunk_files():
    if not CHUNKS_DIR.exists():
        raise FileNotFoundError(
            f"Chunk directory not found: "
            f"{CHUNKS_DIR}"
        )

    return sorted(
        CHUNKS_DIR.glob("*.json")
    )


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

            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            output_stem = data.get(
                "output_stem",
                "",
            )

            if "_" not in output_stem:
                raise ValueError(
                    "Invalid or missing "
                    "output_stem"
                )

            chunks = data.get(
                "chunks",
                [],
            )

            for chunk in chunks:

                if not chunk.get(
                    "chunk_id"
                ):
                    raise ValueError(
                        "Missing chunk_id"
                    )

                if (
                    "chunk_index"
                    not in chunk
                ):
                    raise ValueError(
                        "Missing chunk_index"
                    )

                if not chunk.get("text"):
                    raise ValueError(
                        "Missing chunk text"
                    )

            total_chunks += len(
                chunks
            )

            valid_files += 1

        except Exception as exc:

            errors.append(
                f"{path.name}: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    print("=" * 70)
    print(
        "TENNIS EXPLORE - "
        "CHUNK DATABASE DRY RUN"
    )
    print("=" * 70)

    print(
        f"\nChunk JSON files : "
        f"{len(files)}"
    )

    print(
        f"Valid files      : "
        f"{valid_files}"
    )

    print(
        f"Total chunks     : "
        f"{total_chunks}"
    )

    print(
        f"Errors           : "
        f"{len(errors)}"
    )

    if errors:

        print("\nErrors:")

        for error in errors[:20]:
            print(
                f"  {error}"
            )

    print(
        "\nNO DATABASE CHANGES MADE."
    )

    print("=" * 70)


# ============================================================
# Chunk loading
# ============================================================

def load_chunks():
    config = get_db_config()
    files = get_chunk_files()

    print("=" * 70)
    print(
        "TENNIS EXPLORE - "
        "POSTGRES CHUNK LOADER"
    )
    print("=" * 70)

    print(
        f"\nDatabase         : "
        f"{config['dbname']}"
    )

    print(
        f"Chunk JSON files : "
        f"{len(files)}"
    )

    files_processed = 0
    chunks_processed = 0

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:

            document_map = (
                get_document_id_map(cur)
            )

            print(
                f"Document mappings: "
                f"{len(document_map)}"
            )

            for (
                file_number,
                path,
            ) in enumerate(
                files,
                start=1,
            ):

                with path.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    data = json.load(file)

                output_stem = data.get(
                    "output_stem",
                    "",
                )

                if "_" not in output_stem:
                    raise RuntimeError(
                        "Cannot derive resource_id "
                        f"from {path.name}"
                    )

                resource_id = (
                    output_stem.split(
                        "_",
                        1,
                    )[0]
                )

                document_id = (
                    document_map.get(
                        resource_id
                    )
                )

                if document_id is None:
                    raise RuntimeError(
                        "No PostgreSQL document "
                        "found for "
                        f"resource_id="
                        f"{resource_id} "
                        f"({path.name})"
                    )

                chunks = data.get(
                    "chunks",
                    [],
                )

                records = [
                    build_chunk_record(
                        document_id,
                        chunk,
                    )
                    for chunk in chunks
                ]

                if records:
                    cur.executemany(
                        INSERT_CHUNK_SQL,
                        records,
                    )

                files_processed += 1

                chunks_processed += len(
                    records
                )

                # Commit after each source
                # document so the load is
                # resumable.

                conn.commit()

                if (
                    file_number % 100 == 0
                    or file_number
                    == len(files)
                ):
                    print(
                        f"Processed files : "
                        f"{file_number}/"
                        f"{len(files)} | "
                        f"Chunks : "
                        f"{chunks_processed}"
                    )

    print()
    print("=" * 70)
    print(
        "CHUNK LOADING COMPLETE"
    )
    print("=" * 70)

    print(
        f"Files processed : "
        f"{files_processed}"
    )

    print(
        f"Chunks processed: "
        f"{chunks_processed}"
    )


# ============================================================
# Document dry run
# ============================================================

def document_dry_run(records):
    config = get_db_config()

    print("=" * 70)
    print(
        "TENNIS EXPLORE - "
        "POSTGRES LOAD DRY RUN"
    )
    print("=" * 70)

    print(
        f"\nDatabase : {config['dbname']}"
    )

    print(
        f"Host     : {config['host']}"
    )

    print(
        f"Port     : {config['port']}"
    )

    print(
        f"User     : {config['user']}"
    )

    print(
        "\nDocuments that would be "
        f"loaded : {len(records)}"
    )

    if records:

        print("\nSample record:")

        for key, value in (
            records[0].items()
        ):
            print(
                f"{key:<20}: {value}"
            )

    print(
        "\nNO DATABASE CHANGES MADE."
    )

    print("=" * 70)


# ============================================================
# Incremental sync detection
# ============================================================

def get_database_document_state():
    """
    Return current database document state
    keyed by resource_id.
    """

    config = get_db_config()

    query = """
        SELECT
            resource_id,
            etag,
            last_modified
        FROM unstructured.documents;
    """

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:

            cur.execute(query)
            rows = cur.fetchall()

    return {
        resource_id: {
            "etag": etag,
            "last_modified": (
                last_modified.isoformat()
                if last_modified
                is not None
                else None
            ),
        }
        for (
            resource_id,
            etag,
            last_modified,
        ) in rows
    }


def normalize_value(value):
    if value is None:
        return ""

    return str(value).strip()


def classify_sync_records(
    records,
    database_state,
):
    """
    Classify manifest records as:
    - new
    - changed
    - unchanged
    """

    new_documents = []
    changed_documents = []
    unchanged_documents = []

    for record in records:

        resource_id = record[
            "resource_id"
        ]

        existing = database_state.get(
            resource_id
        )

        if existing is None:

            new_documents.append(
                record
            )

            continue

        manifest_etag = normalize_value(
            record.get("etag")
        )

        database_etag = normalize_value(
            existing.get("etag")
        )

        if (
            manifest_etag
            == database_etag
        ):
            unchanged_documents.append(
                record
            )

        else:
            changed_documents.append(
                record
            )

    return (
        new_documents,
        changed_documents,
        unchanged_documents,
    )


def sync_dry_run(records):
    """
    Compare production manifest with PostgreSQL.

    This function DOES NOT modify the database.
    """

    print("=" * 70)
    print(
        "TENNIS EXPLORE - "
        "INCREMENTAL DATABASE "
        "SYNC DRY RUN"
    )
    print("=" * 70)

    print()
    print(
        "Reading current database state..."
    )

    database_state = (
        get_database_document_state()
    )

    (
        new_documents,
        changed_documents,
        unchanged_documents,
    ) = classify_sync_records(
        records,
        database_state,
    )

    print(
        f"Manifest documents : "
        f"{len(records)}"
    )

    print(
        f"Database documents : "
        f"{len(database_state)}"
    )

    print()
    print("=" * 70)
    print("SYNC COMPARISON")
    print("=" * 70)

    print(
        f"New documents       : "
        f"{len(new_documents)}"
    )

    print(
        f"Changed documents   : "
        f"{len(changed_documents)}"
    )

    print(
        f"Unchanged documents : "
        f"{len(unchanged_documents)}"
    )

    if new_documents:

        print()
        print("New documents:")

        for record in (
            new_documents[:20]
        ):
            print(
                f"  + "
                f"{record['file_name']}"
            )

    if changed_documents:

        print()
        print("Changed documents:")

        for record in (
            changed_documents[:20]
        ):
            print(
                f"  * "
                f"{record['file_name']}"
            )

    print()
    print(
        "NO DATABASE CHANGES MADE."
    )

    print("=" * 70)


# ============================================================
# Incremental database synchronization helpers
# ============================================================

def find_chunk_file(resource_id):
    """
    Find the production chunk JSON belonging
    to one resource_id.
    """

    matches = sorted(
        CHUNKS_DIR.glob(
            f"{resource_id}_*.json"
        )
    )

    if len(matches) > 1:
        raise RuntimeError(
            "Multiple chunk files found "
            f"for resource_id={resource_id}"
        )

    if not matches:
        return None

    return matches[0]


def load_and_validate_chunk_file(
    path,
    expected_resource_id,
):
    """
    Load one chunk JSON and validate that it
    belongs to the expected document.
    """

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    output_stem = data.get(
        "output_stem",
        "",
    )

    if "_" not in output_stem:
        raise ValueError(
            "Invalid output_stem in "
            f"{path.name}"
        )

    resource_id = output_stem.split(
        "_",
        1,
    )[0]

    if (
        resource_id
        != expected_resource_id
    ):
        raise ValueError(
            "Chunk file resource_id "
            "mismatch: "
            f"expected="
            f"{expected_resource_id}, "
            f"found={resource_id}"
        )

    chunks = data.get(
        "chunks",
        [],
    )

    if not isinstance(
        chunks,
        list,
    ):
        raise ValueError(
            "Invalid chunks value in "
            f"{path.name}"
        )

    for chunk in chunks:

        if not chunk.get(
            "chunk_id"
        ):
            raise ValueError(
                "Missing chunk_id in "
                f"{path.name}"
            )

        if (
            "chunk_index"
            not in chunk
        ):
            raise ValueError(
                "Missing chunk_index in "
                f"{path.name}"
            )

        if not chunk.get("text"):
            raise ValueError(
                "Missing chunk text in "
                f"{path.name}"
            )

    return chunks


def prepare_sync_document(record):
    """
    Validate local chunk artifacts BEFORE
    any destructive database operation.

    Returns:
        chunk list for chunked documents
        [] for valid zero-chunk documents
    """

    resource_id = record[
        "resource_id"
    ]

    chunk_count = int(
        record.get(
            "chunk_count"
        ) or 0
    )

    extraction_status = (
        record.get(
            "extraction_status"
        ) or ""
    )

    chunking_status = (
        record.get(
            "chunking_status"
        ) or ""
    )

    chunk_file = find_chunk_file(
        resource_id
    )

    # -----------------------------------------------------
    # Document expects chunks
    # -----------------------------------------------------

    if chunk_count > 0:

        if chunk_file is None:
            raise FileNotFoundError(
                f"Manifest expects "
                f"{chunk_count} chunks "
                "but no chunk JSON exists "
                f"for resource_id="
                f"{resource_id}"
            )

        chunks = (
            load_and_validate_chunk_file(
                chunk_file,
                resource_id,
            )
        )

        if (
            len(chunks)
            != chunk_count
        ):
            raise ValueError(
                "Chunk count mismatch for "
                f"resource_id="
                f"{resource_id}: "
                f"manifest="
                f"{chunk_count}, "
                f"file={len(chunks)}"
            )

        return chunks

    # -----------------------------------------------------
    # Zero-chunk document
    # -----------------------------------------------------

    allowed_zero_chunk_states = {
        "needs_ocr",
        "invalid_pptx",
        "failed",
    }

    allowed_zero_chunking_states = {
        "skipped",
        "skipped_needs_ocr",
        "skipped_invalid_pptx",
    }

    if (
        extraction_status
        in allowed_zero_chunk_states
        or chunking_status
        in allowed_zero_chunking_states
    ):
        return []

    # Some successfully extracted documents
    # genuinely produce zero usable chunks.

    if chunk_file is not None:

        chunks = (
            load_and_validate_chunk_file(
                chunk_file,
                resource_id,
            )
        )

        if chunks:
            raise ValueError(
                "Manifest says zero chunks "
                f"but {len(chunks)} chunks "
                "exist for resource_id="
                f"{resource_id}"
            )

        return []

    raise RuntimeError(
        "Zero-chunk document has no "
        "valid supporting state or "
        "chunk file: "
        f"resource_id={resource_id}"
    )


# ============================================================
# Incremental database synchronization
# ============================================================

def sync_database(records):
    """
    Synchronize only new or changed
    production documents.

    New:
        upsert document
        insert current chunks

    Changed:
        validate replacement artifacts first
        update document
        delete old chunks
        insert current chunks

    Each document is committed independently.
    """

    config = get_db_config()

    print("=" * 70)
    print(
        "TENNIS EXPLORE - "
        "INCREMENTAL DATABASE "
        "SYNCHRONIZATION"
    )
    print("=" * 70)

    print()
    print(
        "Reading current database state..."
    )

    database_state = (
        get_database_document_state()
    )

    (
        new_documents,
        changed_documents,
        unchanged_documents,
    ) = classify_sync_records(
        records,
        database_state,
    )

    print(
        f"Manifest documents : "
        f"{len(records)}"
    )

    print(
        f"Database documents : "
        f"{len(database_state)}"
    )

    print()

    print(
        f"New documents       : "
        f"{len(new_documents)}"
    )

    print(
        f"Changed documents   : "
        f"{len(changed_documents)}"
    )

    print(
        f"Unchanged documents : "
        f"{len(unchanged_documents)}"
    )

    pending = [
        (
            "new",
            record,
        )
        for record
        in new_documents
    ] + [
        (
            "changed",
            record,
        )
        for record
        in changed_documents
    ]

    # -----------------------------------------------------
    # Nothing to synchronize
    # -----------------------------------------------------

    if not pending:

        print()
        print("=" * 70)

        print(
            "DATABASE IS ALREADY "
            "SYNCHRONIZED"
        )

        print("=" * 70)

        print()
        print(
            "No database changes "
            "were made."
        )

        return

    # -----------------------------------------------------
    # Validate ALL local artifacts before writing
    # -----------------------------------------------------

    print()
    print(
        "Validating pending chunk "
        "artifacts before database "
        "changes..."
    )

    prepared = []

    for (
        status,
        record,
    ) in pending:

        chunks = prepare_sync_document(
            record
        )

        prepared.append(
            (
                status,
                record,
                chunks,
            )
        )

    print(
        "Pending documents "
        f"validated : {len(prepared)}"
    )

    # -----------------------------------------------------
    # Synchronize database
    # -----------------------------------------------------

    documents_synced = 0
    chunks_inserted = 0
    old_chunks_removed = 0

    with psycopg.connect(**config) as conn:

        for (
            status,
            record,
            chunks,
        ) in prepared:

            try:

                with conn.cursor() as cur:

                    # -------------------------------------
                    # Upsert document metadata
                    # -------------------------------------

                    cur.execute(
                        INSERT_DOCUMENT_SQL,
                        record,
                    )

                    cur.execute(
                        """
                        SELECT document_id
                        FROM unstructured.documents
                        WHERE resource_id = %s;
                        """,
                        (
                            record[
                                "resource_id"
                            ],
                        ),
                    )

                    result = cur.fetchone()

                    if result is None:
                        raise RuntimeError(
                            "Document ID could "
                            "not be resolved "
                            "after upsert."
                        )

                    document_id = (
                        result[0]
                    )

                    # -------------------------------------
                    # Changed document:
                    # remove previous chunks
                    # -------------------------------------

                    removed_this_document = 0

                    if status == "changed":

                        cur.execute(
                            """
                            DELETE FROM
                                unstructured.document_chunks
                            WHERE document_id = %s;
                            """,
                            (
                                document_id,
                            ),
                        )

                        removed_this_document = (
                            cur.rowcount
                            if cur.rowcount
                            is not None
                            else 0
                        )

                    # -------------------------------------
                    # Insert current chunks
                    # -------------------------------------

                    chunk_records = [
                        build_chunk_record(
                            document_id,
                            chunk,
                        )
                        for chunk in chunks
                    ]

                    if chunk_records:

                        cur.executemany(
                            INSERT_CHUNK_SQL,
                            chunk_records,
                        )

                    # -------------------------------------
                    # Verify database chunk count
                    # -------------------------------------

                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM
                            unstructured.document_chunks
                        WHERE document_id = %s;
                        """,
                        (
                            document_id,
                        ),
                    )

                    database_chunk_count = (
                        cur.fetchone()[0]
                    )

                    expected_chunk_count = (
                        len(chunk_records)
                    )

                    if (
                        database_chunk_count
                        != expected_chunk_count
                    ):
                        raise RuntimeError(
                            "Database chunk count "
                            "verification failed "
                            "for resource_id="
                            f"{record['resource_id']}: "
                            "expected="
                            f"{expected_chunk_count}, "
                            "database="
                            f"{database_chunk_count}"
                        )

                    # -------------------------------------
                    # Commit this document transaction
                    # -------------------------------------

                    conn.commit()

                    documents_synced += 1

                    chunks_inserted += (
                        len(chunk_records)
                    )

                    old_chunks_removed += (
                        removed_this_document
                    )

                    print(
                        f"[{documents_synced}/"
                        f"{len(prepared)}] "
                        f"{status.upper()} | "
                        f"{record['file_name']} | "
                        "chunks="
                        f"{len(chunk_records)}"
                    )

            except Exception:

                conn.rollback()

                raise

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print()
    print("=" * 70)

    print(
        "DATABASE SYNCHRONIZATION "
        "COMPLETE"
    )

    print("=" * 70)

    print(
        f"Documents synchronized : "
        f"{documents_synced}"
    )

    print(
        f"Old chunks removed     : "
        f"{old_chunks_removed}"
    )

    print(
        f"Current chunks inserted: "
        f"{chunks_inserted}"
    )

    print()
    print(
        "Run "
        "update_production_embeddings.py "
        "next to synchronize retrieval "
        "artifacts."
    )


# ============================================================
# Entry point
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Tennis Explore PostgreSQL "
            "production data loader"
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Dry run for document records."
        ),
    )

    parser.add_argument(
        "--load-documents",
        action="store_true",
        help=(
            "Load/upsert all document records."
        ),
    )

    parser.add_argument(
        "--chunk-dry-run",
        action="store_true",
        help=(
            "Validate chunk files before "
            "database loading."
        ),
    )

    parser.add_argument(
        "--load-chunks",
        action="store_true",
        help=(
            "Load/upsert all chunks into "
            "PostgreSQL."
        ),
    )

    parser.add_argument(
        "--sync-dry-run",
        action="store_true",
        help=(
            "Compare production manifest "
            "with PostgreSQL without "
            "making changes."
        ),
    )

    parser.add_argument(
        "--sync",
        action="store_true",
        help=(
            "Synchronize only new or "
            "changed production documents "
            "with PostgreSQL."
        ),
    )

    args = parser.parse_args()

    selected = sum(
        [
            args.dry_run,
            args.load_documents,
            args.chunk_dry_run,
            args.load_chunks,
            args.sync_dry_run,
            args.sync,
        ]
    )

    if selected != 1:

        parser.error(
            "Choose exactly one operation: "
            "--dry-run, "
            "--load-documents, "
            "--chunk-dry-run, "
            "--load-chunks, "
            "--sync-dry-run, "
            "or --sync"
        )

    # -----------------------------------------------------
    # Operations that do not require manifest loading here
    # -----------------------------------------------------

    if args.chunk_dry_run:
        chunk_dry_run()
        return

    if args.load_chunks:
        load_chunks()
        return

    # -----------------------------------------------------
    # Manifest-based operations
    # -----------------------------------------------------

    records = load_manifest()

    if args.sync_dry_run:
        sync_dry_run(
            records
        )
        return

    if args.sync:
        sync_database(
            records
        )
        return

    if args.dry_run:
        document_dry_run(
            records
        )
        return

    if args.load_documents:
        load_documents(
            records
        )
        return


if __name__ == "__main__":
    main()