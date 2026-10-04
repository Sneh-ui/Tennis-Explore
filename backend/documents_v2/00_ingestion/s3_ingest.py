import csv
import sys
from pathlib import Path

import boto3


# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))


# ---------------------------------------------------------
# S3 SETTINGS
# ---------------------------------------------------------

BUCKET_NAME = "tennis-explore-resources"

PREFIX = (
    "unstructured-data/"
    "document-resources/"
)

MAX_FILE_SIZE_MB = 250


# ---------------------------------------------------------
# OUTPUT PATHS
# ---------------------------------------------------------

OUTPUT_DIR = (
    DOCUMENTS_V2_DIR
    / "outputs"
    / "production"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PLAN_PATH = (
    OUTPUT_DIR
    / "s3_ingestion_plan.csv"
)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def bytes_to_mb(size_bytes):
    return round(
        size_bytes / (1024 * 1024),
        3,
    )


def classify_object(key, size_bytes):
    """
    Classify an S3 object for production ingestion.
    """

    suffix = Path(key).suffix.lower()
    size_mb = bytes_to_mb(size_bytes)

    if suffix == ".pdf":
        file_type = "pdf"
        supported = True

    elif suffix == ".pptx":
        file_type = "pptx"
        supported = True

    elif suffix == ".ppt":
        return {
            "file_type": "ppt",
            "status": "unsupported_format",
            "supported": False,
            "reason": "Legacy PPT format is not supported by python-pptx.",
        }

    elif suffix == ".zip":
        return {
            "file_type": "zip",
            "status": "unsupported_format",
            "supported": False,
            "reason": "ZIP archives are not processed by the document pipeline.",
        }

    else:
        return {
            "file_type": suffix.lstrip(".") or "unknown",
            "status": "unsupported_format",
            "supported": False,
            "reason": "Unsupported file extension.",
        }

    if size_mb > MAX_FILE_SIZE_MB:
        return {
            "file_type": file_type,
            "status": "deferred_large_file",
            "supported": False,
            "reason": (
                f"File exceeds current safety limit "
                f"of {MAX_FILE_SIZE_MB} MB."
            ),
        }

    return {
        "file_type": file_type,
        "status": "ready",
        "supported": supported,
        "reason": "",
    }


# ---------------------------------------------------------
# S3 DISCOVERY
# ---------------------------------------------------------

def discover_objects():
    """
    Read all object metadata under the production
    document prefix.

    No files are downloaded.
    """

    s3 = boto3.client("s3")

    paginator = s3.get_paginator(
        "list_objects_v2"
    )

    rows = []

    page_number = 0

    print()
    print("=" * 72)
    print("TENNIS EXPLORE - PRODUCTION S3 INGESTION DRY RUN")
    print("=" * 72)

    print()
    print(f"Bucket : {BUCKET_NAME}")
    print(f"Prefix : {PREFIX}")
    print(
        f"Large-file threshold : "
        f"{MAX_FILE_SIZE_MB} MB"
    )

    print()
    print("Reading S3 object metadata...")

    for page in paginator.paginate(
        Bucket=BUCKET_NAME,
        Prefix=PREFIX,
    ):
        page_number += 1

        contents = page.get(
            "Contents",
            [],
        )

        print(
            f"Processed S3 page "
            f"{page_number} "
            f"({len(contents)} objects)"
        )

        for obj in contents:
            key = obj["Key"]

            # Skip folder placeholders.
            if key.endswith("/"):
                continue

            size_bytes = obj["Size"]
            size_mb = bytes_to_mb(
                size_bytes
            )

            classification = (
                classify_object(
                    key,
                    size_bytes,
                )
            )

            rows.append(
                {
                    "s3_key": key,
                    "file_name":
                        Path(key).name,
                    "file_type":
                        classification[
                            "file_type"
                        ],
                    "size_bytes":
                        size_bytes,
                    "size_mb":
                        size_mb,
                    "last_modified":
                        obj[
                            "LastModified"
                        ].isoformat(),
                    "etag":
                        obj.get(
                            "ETag",
                            "",
                        ).replace(
                            '"',
                            "",
                        ),
                    "status":
                        classification[
                            "status"
                        ],
                    "supported":
                        classification[
                            "supported"
                        ],
                    "reason":
                        classification[
                            "reason"
                        ],
                }
            )

    return rows


# ---------------------------------------------------------
# SAVE PLAN
# ---------------------------------------------------------

def save_plan(rows):
    fieldnames = [
        "s3_key",
        "file_name",
        "file_type",
        "size_bytes",
        "size_mb",
        "last_modified",
        "etag",
        "status",
        "supported",
        "reason",
    ]

    with PLAN_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

def print_summary(rows):
    counts = {}

    total_size_mb = 0

    for row in rows:
        status = row["status"]

        counts[status] = (
            counts.get(
                status,
                0,
            )
            + 1
        )

        total_size_mb += (
            row["size_mb"]
        )

    print()
    print("=" * 72)
    print("DRY RUN SUMMARY")
    print("=" * 72)

    print()
    print(
        f"Objects discovered      : "
        f"{len(rows)}"
    )

    print(
        f"Total size (MB)         : "
        f"{total_size_mb:.3f}"
    )

    print()
    print(
        f"Ready for processing    : "
        f"{counts.get('ready', 0)}"
    )

    print(
        f"Deferred large files    : "
        f"{counts.get('deferred_large_file', 0)}"
    )

    print(
        f"Unsupported formats     : "
        f"{counts.get('unsupported_format', 0)}"
    )

    print()

    type_counts = {}

    for row in rows:
        file_type = row[
            "file_type"
        ]

        type_counts[file_type] = (
            type_counts.get(
                file_type,
                0,
            )
            + 1
        )

    print("FILE TYPE COUNTS")
    print("-" * 72)

    for file_type in sorted(
        type_counts
    ):
        print(
            f"{file_type.upper():8} : "
            f"{type_counts[file_type]}"
        )

    print()
    print(
        f"Ingestion plan saved to:"
    )
    print(
        PLAN_PATH
    )

    print()
    print(
        "DRY RUN ONLY - "
        "NO FILES WERE DOWNLOADED."
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    rows = discover_objects()

    if not rows:
        print()
        print(
            "No objects were found "
            "under the configured prefix."
        )
        return

    save_plan(
        rows
    )

    print_summary(
        rows
    )


if __name__ == "__main__":
    main()