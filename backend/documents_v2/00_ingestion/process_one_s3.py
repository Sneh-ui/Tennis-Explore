import csv
import importlib.util
import sys
from pathlib import Path

import boto3


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import EXTRACTION_OUTPUT_DIR


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

TEMP_DIR = (
    DOCUMENTS_V2_DIR
    / "outputs"
    / "production"
    / "temp_download"
)

TEMP_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ---------------------------------------------------------
# LOAD EXISTING PIPELINE MODULES
# ---------------------------------------------------------

def load_module(module_name, path):
    """
    Load a Python file directly by path.

    This is required because folders such as
    02_extraction and 03_chunking begin with numbers
    and cannot be imported normally.
    """

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
# READ INGESTION PLAN
# ---------------------------------------------------------

def load_ready_files():
    """
    Read the dry-run ingestion plan and return
    production files marked ready.
    """

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
# SELECT ONE SAFE TEST FILE
# ---------------------------------------------------------

def select_test_file(rows):
    """
    Select one small production file for the first
    S3-to-pipeline validation.

    Prefer a file between 0.1 MB and 5 MB so the test
    is realistic but still quick and safe.
    """

    preferred = [
        row
        for row in rows
        if 0.1 <= row["size_mb"] <= 5
    ]

    if preferred:
        preferred.sort(
            key=lambda row:
                row["size_mb"]
        )

        return preferred[0]

    # Fallback: smallest ready file.
    rows.sort(
        key=lambda row:
            row["size_mb"]
    )

    return rows[0]


# ---------------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------------

def download_object(s3, row):
    """
    Download one production S3 object to a temporary
    local location.
    """

    local_path = (
        TEMP_DIR
        / row["file_name"]
    )

    print()
    print("Downloading production test file...")
    print(
        f"S3 key : {row['s3_key']}"
    )
    print(
        f"Size   : {row['size_mb']} MB"
    )
    print(
        f"Local  : {local_path}"
    )

    s3.download_file(
        BUCKET_NAME,
        row["s3_key"],
        str(local_path),
    )

    return local_path


# ---------------------------------------------------------
# PROCESS ONE FILE
# ---------------------------------------------------------

def process_file(local_path):
    """
    Run the existing V2 extraction and chunking pipeline.
    """

    print()
    print("=" * 72)
    print("STEP 1 - EXTRACTION")
    print("=" * 72)

    extraction_result = (
        extraction_module.process_document(
            local_path
        )
    )

    if not extraction_result:
        raise RuntimeError(
            "Extraction returned no result."
        )

    status = extraction_result.get(
        "status"
    )

    print()
    print(
        f"Extraction status: {status}"
    )

    if status == "needs_ocr":
        print()
        print(
            "This production document requires OCR."
        )
        print(
            "Chunking will not be performed."
        )

        return {
            "extraction_status":
                status,
            "chunk_status":
                "skipped_needs_ocr",
        }

    if status == "failed":
        print()
        print(
            "Extraction failed."
        )

        return {
            "extraction_status":
                status,
            "chunk_status":
                "skipped_failed",
        }

    # process_document() saves:
    # <filename>_extracted.json
    extracted_path = (
        EXTRACTION_OUTPUT_DIR
        / (
            f"{local_path.stem}"
            "_extracted.json"
        )
    )

    if not extracted_path.exists():
        raise FileNotFoundError(
            f"Expected extracted JSON "
            f"not found: {extracted_path}"
        )

    print()
    print("=" * 72)
    print("STEP 2 - CHUNKING")
    print("=" * 72)

    chunk_result = (
        chunking_module
        .process_extracted_document(
            extracted_path
        )
    )

    if chunk_result is None:
        chunk_status = "skipped"
    else:
        chunk_status = "success"

    return {
        "extraction_status":
            status,
        "chunk_status":
            chunk_status,
    }


# ---------------------------------------------------------
# CLEANUP
# ---------------------------------------------------------

def cleanup_temp_file(path):
    """
    Delete only the temporary local copy.

    The original S3 object is never modified.
    """

    if path.exists():

        path.unlink()

        print()
        print(
            "Temporary local file deleted."
        )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print()
    print("=" * 72)
    print(
        "TENNIS EXPLORE - "
        "ONE FILE S3 PRODUCTION TEST"
    )
    print("=" * 72)

    rows = load_ready_files()

    print()
    print(
        f"Ready production files: "
        f"{len(rows)}"
    )

    if not rows:
        print(
            "No ready production files found."
        )
        return

    selected = select_test_file(
        rows
    )

    print()
    print("Selected test object:")
    print(
        f"File : {selected['file_name']}"
    )
    print(
        f"Type : {selected['file_type'].upper()}"
    )
    print(
        f"Size : {selected['size_mb']} MB"
    )
    print(
        f"Key  : {selected['s3_key']}"
    )

    s3 = boto3.client(
        "s3"
    )

    local_path = None

    try:

        local_path = download_object(
            s3,
            selected,
        )

        result = process_file(
            local_path
        )

        print()
        print("=" * 72)
        print("PRODUCTION TEST RESULT")
        print("=" * 72)

        print()
        print(
            f"File              : "
            f"{selected['file_name']}"
        )

        print(
            f"Extraction status : "
            f"{result['extraction_status']}"
        )

        print(
            f"Chunking status   : "
            f"{result['chunk_status']}"
        )

        print()
        print(
            "Original S3 object was not modified."
        )

    except Exception as exc:

        print()
        print("=" * 72)
        print("PRODUCTION TEST FAILED")
        print("=" * 72)

        print()
        print(
            f"Error type : "
            f"{type(exc).__name__}"
        )

        print(
            f"Message    : "
            f"{exc}"
        )

    finally:

        if local_path:
            cleanup_temp_file(
                local_path
            )


if __name__ == "__main__":
    main()