import csv
from pathlib import Path
from collections import Counter


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


# ============================================================
# Helpers
# ============================================================

def parse_bool(value):
    """
    Convert common text values into Python booleans.
    """
    if value is None:
        return False

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "y",
    }


def mb_to_bytes(value):
    """
    Convert size in MB from the production manifest
    into an approximate byte count.
    """
    if value is None or str(value).strip() == "":
        return None

    try:
        return int(float(value) * 1024 * 1024)
    except (TypeError, ValueError):
        return None


def build_document_record(row):
    """
    Convert one production manifest row into the structure
    expected by unstructured.documents.
    """

    extraction_status = (
        row.get("extraction_status") or ""
    ).strip()

    requires_ocr = extraction_status == "needs_ocr"

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
        ).strip(),

        "last_modified": (
            row.get("last_modified") or ""
        ).strip(),

        "processing_status": (
            row.get("processing_status") or ""
        ).strip(),

        "extraction_status": extraction_status,

        "chunking_status": (
            row.get("chunking_status") or ""
        ).strip(),

        "chunk_count": int(
            row.get("chunk_count") or 0
        ),

        "processed_at": (
            row.get("processed_at") or ""
        ).strip() or None,

        "requires_ocr": requires_ocr,

        "error_type": (
            row.get("error_type") or ""
        ).strip() or None,

        "error_message": (
            row.get("error_message") or ""
        ).strip() or None,
    }


def validate_record(record):
    """
    Validate fields required by the proposed database schema.
    """

    errors = []

    required_fields = [
        "resource_id",
        "source_system",
        "source_location",
        "file_name",
        "file_type",
    ]

    for field in required_fields:
        if not record.get(field):
            errors.append(
                f"Missing required field: {field}"
            )

    return errors


# ============================================================
# Dry run
# ============================================================

def dry_run():
    print("=" * 70)
    print("TENNIS EXPLORE - DOCUMENT DATABASE DRY RUN")
    print("=" * 70)

    print("\nManifest:")
    print(MANIFEST_PATH)

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

    print(f"\nManifest rows found : {len(rows)}")

    valid_records = []
    invalid_records = []

    resource_ids = []

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        record = build_document_record(row)

        errors = validate_record(record)

        if errors:
            invalid_records.append(
                {
                    "row_number": row_number,
                    "file_name": record["file_name"],
                    "errors": errors,
                }
            )
        else:
            valid_records.append(record)

        if record["resource_id"]:
            resource_ids.append(
                record["resource_id"]
            )

    # --------------------------------------------------------
    # Duplicate resource IDs
    # --------------------------------------------------------

    id_counts = Counter(resource_ids)

    duplicate_ids = {
        resource_id: count
        for resource_id, count in id_counts.items()
        if count > 1
    }

    # --------------------------------------------------------
    # Status summaries
    # --------------------------------------------------------

    processing_statuses = Counter(
        record["processing_status"]
        for record in valid_records
    )

    extraction_statuses = Counter(
        record["extraction_status"]
        for record in valid_records
    )

    file_types = Counter(
        record["file_type"]
        for record in valid_records
    )

    ocr_count = sum(
        1
        for record in valid_records
        if record["requires_ocr"]
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("VALIDATION SUMMARY")
    print("-" * 70)

    print(
        f"Valid records       : {len(valid_records)}"
    )

    print(
        f"Invalid records     : {len(invalid_records)}"
    )

    print(
        f"Duplicate resource IDs : {len(duplicate_ids)}"
    )

    print(
        f"Requires OCR        : {ocr_count}"
    )

    print("\nFile types:")
    for key, value in sorted(file_types.items()):
        print(f"  {key:<20} {value}")

    print("\nProcessing statuses:")
    for key, value in sorted(
        processing_statuses.items()
    ):
        print(f"  {key or '(blank)':<20} {value}")

    print("\nExtraction statuses:")
    for key, value in sorted(
        extraction_statuses.items()
    ):
        print(f"  {key or '(blank)':<20} {value}")

    # --------------------------------------------------------
    # Invalid records
    # --------------------------------------------------------

    if invalid_records:
        print("\n" + "-" * 70)
        print("INVALID RECORDS")
        print("-" * 70)

        for item in invalid_records[:20]:
            print(
                f"\nCSV row: {item['row_number']}"
            )
            print(
                f"File   : {item['file_name']}"
            )

            for error in item["errors"]:
                print(f"  - {error}")

    # --------------------------------------------------------
    # Duplicate IDs
    # --------------------------------------------------------

    if duplicate_ids:
        print("\n" + "-" * 70)
        print("DUPLICATE RESOURCE IDs")
        print("-" * 70)

        for resource_id, count in list(
            duplicate_ids.items()
        )[:20]:
            print(
                f"{resource_id}: {count} records"
            )

    # --------------------------------------------------------
    # Sample mapping
    # --------------------------------------------------------

    if valid_records:
        print("\n" + "-" * 70)
        print("SAMPLE DATABASE RECORD")
        print("-" * 70)

        sample = valid_records[0]

        for key, value in sample.items():
            print(f"{key:<20}: {value}")

    print("\n" + "=" * 70)

    if (
        len(invalid_records) == 0
        and len(duplicate_ids) == 0
    ):
        print(
            "DRY RUN PASSED - records are ready "
            "for database loading."
        )
    else:
        print(
            "DRY RUN FOUND ISSUES - review before "
            "database loading."
        )

    print("=" * 70)


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    dry_run()