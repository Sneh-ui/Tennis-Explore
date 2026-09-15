import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import boto3


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))


# ---------------------------------------------------------
# AWS SETTINGS
# ---------------------------------------------------------

BUCKET_NAME = "tennis-explore-resources"

INGESTION_PLAN = (
    DOCUMENTS_V2_DIR
    / "outputs"
    / "production"
    / "s3_ingestion_plan.csv"
)


# ---------------------------------------------------------
# PRODUCTION OUTPUT DIRECTORIES
# ---------------------------------------------------------

PRODUCTION_DIR = (
    DOCUMENTS_V2_DIR
    / "outputs"
    / "production"
)

PRODUCTION_EXTRACTED_DIR = (
    PRODUCTION_DIR
    / "extracted"
)

PRODUCTION_CHUNKS_DIR = (
    PRODUCTION_DIR
    / "chunks"
)

TEMP_DIR = (
    PRODUCTION_DIR
    / "temp_download"
)

MANIFEST_PATH = (
    PRODUCTION_DIR
    / "processing_manifest.csv"
)

for directory in [
    PRODUCTION_DIR,
    PRODUCTION_EXTRACTED_DIR,
    PRODUCTION_CHUNKS_DIR,
    TEMP_DIR,
]:
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


# ---------------------------------------------------------
# LOAD EXISTING PIPELINE MODULES
# ---------------------------------------------------------

def load_module(
    module_name,
    path,
):
    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


extraction_module = load_module(
    "v2_extraction",
    DOCUMENTS_V2_DIR
    / "02_extraction"
    / "extract_documents.py",
)

chunking_module = load_module(
    "v2_chunking",
    DOCUMENTS_V2_DIR
    / "03_chunking"
    / "chunk_documents.py",
)


# ---------------------------------------------------------
# PRODUCTION OUTPUT OVERRIDES
# ---------------------------------------------------------

extraction_module.EXTRACTION_OUTPUT_DIR = (
    PRODUCTION_EXTRACTED_DIR
)

chunking_module.CHUNK_OUTPUT_DIR = (
    PRODUCTION_CHUNKS_DIR
)


# ---------------------------------------------------------
# MANIFEST
# ---------------------------------------------------------

MANIFEST_FIELDS = [
    "resource_id",
    "s3_key",
    "etag",
    "last_modified",
    "file_name",
    "file_type",
    "size_mb",
    "processing_status",
    "extraction_status",
    "chunking_status",
    "chunk_count",
    "processed_at",
    "error_type",
    "error_message",
]


def load_manifest():
    if not MANIFEST_PATH.exists():
        return {}

    records = {}

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:
            records[
                row["s3_key"]
            ] = row

    return records


def save_manifest(records):
    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=MANIFEST_FIELDS,
        )

        writer.writeheader()

        for key in sorted(
            records
        ):
            writer.writerow(
                records[key]
            )


# ---------------------------------------------------------
# INGESTION PLAN
# ---------------------------------------------------------

def load_ready_plan():
    if not INGESTION_PLAN.exists():
        raise FileNotFoundError(
            f"Ingestion plan not found: "
            f"{INGESTION_PLAN}"
        )

    rows = []

    with INGESTION_PLAN.open(
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            if row["status"] != "ready":
                continue

            if row["file_type"] not in {
                "pdf",
                "pptx",
            }:
                continue

            row["size_mb"] = float(
                row["size_mb"]
            )

            rows.append(
                row
            )

    return rows


# ---------------------------------------------------------
# RESOURCE ID
# ---------------------------------------------------------

def make_resource_id(s3_key):
    """
    Stable deterministic ID derived from the S3 key.

    This prevents filename collisions while remaining
    consistent across repeated runs.
    """

    digest = hashlib.sha256(
        s3_key.encode(
            "utf-8"
        )
    ).hexdigest()

    return digest[:16]


def make_output_stem(
    resource_id,
    file_name,
):
    stem = Path(
        file_name
    ).stem

    safe_stem = "".join(
        character
        if character.isalnum()
        or character in {
            "-",
            "_",
        }
        else "_"
        for character
        in stem
    )

    return (
        f"{resource_id}_"
        f"{safe_stem}"
    )


# ---------------------------------------------------------
# SKIP / CHANGE DETECTION
# ---------------------------------------------------------

def should_skip(
    row,
    manifest_record,
):
    if not manifest_record:
        return False

    if (
        manifest_record.get(
            "processing_status"
        )
        != "processed"
    ):
        return False

    same_etag = (
        manifest_record.get(
            "etag"
        )
        == row.get(
            "etag"
        )
    )

    same_modified = (
        manifest_record.get(
            "last_modified"
        )
        == row.get(
            "last_modified"
        )
    )

    return (
        same_etag
        and same_modified
    )


# ---------------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------------

def download_file(
    s3,
    row,
    output_stem,
):
    suffix = (
        Path(
            row["file_name"]
        )
        .suffix
        .lower()
    )

    local_path = (
        TEMP_DIR
        / f"{output_stem}{suffix}"
    )

    s3.download_file(
        BUCKET_NAME,
        row["s3_key"],
        str(local_path),
    )

    return local_path


# ---------------------------------------------------------
# PROCESS ONE OBJECT
# ---------------------------------------------------------

def process_object(
    s3,
    row,
):
    resource_id = make_resource_id(
        row["s3_key"]
    )

    output_stem = make_output_stem(
        resource_id,
        row["file_name"],
    )

    local_path = None

    source_metadata = {
        "source_system":
            "aws_s3",

        "bucket":
            BUCKET_NAME,

        "s3_key":
            row["s3_key"],

        "etag":
            row.get(
                "etag"
            ),

        "last_modified":
            row.get(
                "last_modified"
            ),

        "resource_id":
            resource_id,
    }

    result = {
        "resource_id":
            resource_id,

        "s3_key":
            row["s3_key"],

        "etag":
            row.get(
                "etag",
                "",
            ),

        "last_modified":
            row.get(
                "last_modified",
                "",
            ),

        "file_name":
            row["file_name"],

        "file_type":
            row["file_type"],

        "size_mb":
            row["size_mb"],

        "processing_status":
            "failed",

        "extraction_status":
            "",

        "chunking_status":
            "",

        "chunk_count":
            0,

        "processed_at":
            "",

        "error_type":
            "",

        "error_message":
            "",
    }

    try:

        print()
        print("-" * 72)
        print(
            f"Processing: "
            f"{row['file_name']}"
        )
        print(
            f"Resource ID: "
            f"{resource_id}"
        )
        print(
            f"Size: "
            f"{row['size_mb']} MB"
        )

        local_path = download_file(
            s3,
            row,
            output_stem,
        )

        extraction_result = (
            extraction_module
            .process_document(
                local_path,
                output_stem=
                    output_stem,
                source_file_name=
                    row[
                        "file_name"
                    ],
                source_metadata=
                    source_metadata,
            )
        )

        if not extraction_result:
            raise RuntimeError(
                "Extraction returned no result."
            )

        extraction_status = (
            extraction_result.get(
                "status",
                "unknown",
            )
        )

        result[
            "extraction_status"
        ] = extraction_status

        if (
            extraction_status
            == "needs_ocr"
        ):
            result[
                "processing_status"
            ] = "processed"

            result[
                "chunking_status"
            ] = "skipped_needs_ocr"

            return result

        if extraction_status == "invalid_pptx":
            result["processing_status"] = "failed"
            result["chunking_status"] = "skipped_invalid_pptx"
            return result

        if extraction_status == "failed":
            raise RuntimeError(
                "Document extraction failed."
            )

        extracted_path = (
            PRODUCTION_EXTRACTED_DIR
            / (
                f"{output_stem}"
                "_extracted.json"
            )
        )

        if not extracted_path.exists():
            raise FileNotFoundError(
                f"Extracted JSON not found: "
                f"{extracted_path}"
            )

        chunk_result = (
            chunking_module
            .process_extracted_document(
                extracted_path,
                output_stem=
                    output_stem,
            )
        )

        if chunk_result is None:
            result[
                "chunking_status"
            ] = "skipped"

            result[
                "chunk_count"
            ] = 0

        else:
            result[
                "chunking_status"
            ] = "success"

            result[
                "chunk_count"
            ] = chunk_result.get(
                "total_chunks",
                0,
            )

        result[
            "processing_status"
        ] = "processed"

        return result

    except Exception as exc:

        result[
            "processing_status"
        ] = "failed"

        result[
            "error_type"
        ] = type(
            exc
        ).__name__

        result[
            "error_message"
        ] = str(
            exc
        )

        return result

    finally:

        result[
            "processed_at"
        ] = (
            datetime.now()
            .astimezone()
            .isoformat()
        )

        if (
            local_path
            and local_path.exists()
        ):
            local_path.unlink()


# ---------------------------------------------------------
# COMMAND-LINE ARGUMENTS
# ---------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Tennis Explore production "
            "S3 ingestion controller"
        )
    )

    group = (
        parser
        .add_mutually_exclusive_group(
            required=True
        )
    )

    group.add_argument(
        "--limit",
        type=int,
        help=(
            "Process at most N new or "
            "changed objects."
        ),
    )

    group.add_argument(
        "--all",
        action="store_true",
        help=(
            "Process all new or "
            "changed ready objects."
        ),
    )

    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help=(
            "Retry objects whose previous "
            "manifest status is failed."
        ),
    )

    parser.add_argument(
        "--file-type",
        choices=[
            "pdf",
            "pptx",
        ],
        help=(
            "Process only the selected "
            "file type."
        ),
    )

    return parser.parse_args()


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    args = parse_args()

    print()
    print("=" * 72)
    print(
        "TENNIS EXPLORE - "
        "PRODUCTION S3 INGESTION"
    )
    print("=" * 72)

    plan = load_ready_plan()

    if args.file_type:
        plan = [
            row
            for row in plan
            if row["file_type"]
            == args.file_type
        ]

    manifest = load_manifest()

    print()
    print(
        f"Ready S3 objects : "
        f"{len(plan)}"
    )

    print(
        f"Manifest records : "
        f"{len(manifest)}"
    )

    pending = []

    skipped_unchanged = 0
    skipped_failed = 0

    for row in plan:

        previous = manifest.get(
            row["s3_key"]
        )

        if (
            previous
            and previous.get(
                "processing_status"
            )
            == "failed"
            and not args.retry_failed
        ):
            skipped_failed += 1
            continue

        if should_skip(
            row,
            previous,
        ):
            skipped_unchanged += 1
            continue

        pending.append(
            row
        )

    print(
        f"Unchanged skipped : "
        f"{skipped_unchanged}"
    )

    print(
        f"Failed skipped    : "
        f"{skipped_failed}"
    )

    print(
        f"Pending objects   : "
        f"{len(pending)}"
    )

    if args.limit is not None:
        pending = pending[
            :args.limit
        ]

    if not pending:
        print()
        print(
            "Nothing to process."
        )
        return

    print()
    print(
        f"This run will process: "
        f"{len(pending)} objects"
    )

    s3 = boto3.client(
        "s3"
    )

    processed = 0
    failed = 0
    needs_ocr = 0
    total_chunks = 0

    for index, row in enumerate(
        pending,
        start=1,
    ):

        print()
        print(
            f"[{index}/{len(pending)}]"
        )

        result = process_object(
            s3,
            row,
        )

        manifest[
            row["s3_key"]
        ] = result

        save_manifest(
            manifest
        )

        if (
            result[
                "processing_status"
            ]
            == "processed"
        ):
            processed += 1

        else:
            failed += 1

        if (
            result[
                "extraction_status"
            ]
            == "needs_ocr"
        ):
            needs_ocr += 1

        total_chunks += int(
            result.get(
                "chunk_count",
                0,
            )
        )

        print(
            f"Status : "
            f"{result['processing_status']}"
        )

        print(
            f"Extract: "
            f"{result['extraction_status']}"
        )

        print(
            f"Chunk  : "
            f"{result['chunking_status']}"
        )

        print(
            f"Chunks : "
            f"{result['chunk_count']}"
        )

        if result[
            "error_message"
        ]:
            print(
                f"Error  : "
                f"{result['error_message']}"
            )

    print()
    print("=" * 72)
    print(
        "PRODUCTION INGESTION SUMMARY"
    )
    print("=" * 72)

    print()
    print(
        f"Objects attempted : "
        f"{len(pending)}"
    )

    print(
        f"Processed         : "
        f"{processed}"
    )

    print(
        f"Needs OCR         : "
        f"{needs_ocr}"
    )

    print(
        f"Failed            : "
        f"{failed}"
    )

    print(
        f"Chunks created    : "
        f"{total_chunks}"
    )

    print()
    print(
        f"Manifest:"
    )
    print(
        MANIFEST_PATH
    )

    print()
    print(
        "Temporary downloads "
        "were removed after processing."
    )


if __name__ == "__main__":
    main()