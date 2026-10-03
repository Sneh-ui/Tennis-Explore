import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    ProfileNotFound,
)

# ---------------------------------------------------------
# Allow config.py to be imported from documents_v2
# ---------------------------------------------------------

CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import (
    S3_BUCKET_NAME,
    S3_DOCUMENT_PREFIX,
    INVENTORY_CSV,
    INVENTORY_SUMMARY_CSV,
)


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def bytes_to_mb(size_bytes):
    """Convert bytes to megabytes."""
    return round(size_bytes / (1024 * 1024), 3)


def get_file_extension(key):
    """
    Return a lowercase file extension without the dot.

    Example:
        report.pdf -> pdf
        slides.PPTX -> pptx
    """
    suffix = Path(key).suffix.lower()

    if not suffix:
        return "no_extension"

    return suffix.lstrip(".")


def get_source_folder(key):
    """
    Return the immediate parent folder containing the file.

    Example:
    unstructured-data/document-resources/research-pdfs/file.pdf
    -> research-pdfs

    unstructured-data/document-resources/powerpoint-folder/file.pptx
    -> powerpoint-folder
    """

    parts = key.strip("/").split("/")

    if len(parts) >= 2:
        return parts[-2]

    return "unknown"


def create_s3_client():
    """
    Create an S3 client.

    boto3 will automatically look for credentials from:
    - AWS CLI configuration
    - environment variables
    - AWS IAM role
    - AWS SSO session
    - other standard AWS credential providers

    Credentials are intentionally NOT hard-coded.
    """
    return boto3.client("s3")


# ---------------------------------------------------------
# LIST S3 OBJECTS
# ---------------------------------------------------------

def list_s3_objects(s3_client, bucket, prefix):
    """
    Safely list all S3 objects beneath a prefix.

    This operation reads object metadata only.
    It does not download, upload, delete or modify files.
    """
    objects = []

    paginator = s3_client.get_paginator("list_objects_v2")

    print()
    print("=" * 70)
    print("S3 PRODUCTION INVENTORY")
    print("=" * 70)
    print(f"Bucket : {bucket}")
    print(f"Prefix : {prefix}")
    print()
    print("Reading S3 object metadata...")
    print()

    page_number = 0

    try:
        for page in paginator.paginate(
            Bucket=bucket,
            Prefix=prefix,
        ):
            page_number += 1

            contents = page.get("Contents", [])

            print(
                f"Processed S3 page {page_number} "
                f"({len(contents)} objects)"
            )

            for obj in contents:
                key = obj["Key"]

                # Ignore folder placeholder objects.
                if key.endswith("/"):
                    continue

                extension = get_file_extension(key)

                size_bytes = obj.get("Size", 0)

                last_modified = obj.get("LastModified")

                if isinstance(last_modified, datetime):
                    last_modified_text = last_modified.isoformat()
                else:
                    last_modified_text = str(last_modified)

                etag = (
                    obj.get("ETag", "")
                    .strip('"')
                )

                record = {
                    "s3_key": key,
                    "file_name": Path(key).name,
                    "file_type": extension,
                    "size_bytes": size_bytes,
                    "size_mb": bytes_to_mb(size_bytes),
                    "etag": etag,
                    "last_modified": last_modified_text,
                    "source_folder": get_source_folder(key),
                }

                objects.append(record)

    except ClientError as exc:
        error_code = (
            exc.response
            .get("Error", {})
            .get("Code", "Unknown")
        )

        print()
        print("AWS returned an error.")
        print(f"Error code: {error_code}")
        print(exc)
        raise

    return objects


# ---------------------------------------------------------
# WRITE FULL INVENTORY
# ---------------------------------------------------------

def write_inventory_csv(records, output_path):
    """Save complete production metadata inventory to CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "s3_key",
        "file_name",
        "file_type",
        "size_bytes",
        "size_mb",
        "etag",
        "last_modified",
        "source_folder",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(records)

    print()
    print(f"Inventory saved to:")
    print(output_path)


# ---------------------------------------------------------
# CREATE SUMMARY
# ---------------------------------------------------------

def build_summary(records):
    """
    Generate summary statistics grouped by file type.
    """

    grouped = defaultdict(list)

    for record in records:
        grouped[record["file_type"]].append(record)

    summary = []

    for file_type, items in sorted(grouped.items()):
        sizes = [
            item["size_bytes"]
            for item in items
        ]

        total_bytes = sum(sizes)

        minimum_bytes = min(sizes) if sizes else 0
        maximum_bytes = max(sizes) if sizes else 0

        average_bytes = (
            total_bytes / len(sizes)
            if sizes
            else 0
        )

        folders = sorted(
            {
                item["source_folder"]
                for item in items
            }
        )

        summary.append(
            {
                "file_type": file_type,
                "file_count": len(items),
                "total_size_mb": bytes_to_mb(total_bytes),
                "smallest_file_mb": bytes_to_mb(minimum_bytes),
                "largest_file_mb": bytes_to_mb(maximum_bytes),
                "average_file_mb": bytes_to_mb(average_bytes),
                "source_folders": "; ".join(folders),
            }
        )

    return summary


def write_summary_csv(summary, output_path):
    """Save summary statistics."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_type",
        "file_count",
        "total_size_mb",
        "smallest_file_mb",
        "largest_file_mb",
        "average_file_mb",
        "source_folders",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(summary)

    print()
    print(f"Summary saved to:")
    print(output_path)


# ---------------------------------------------------------
# CONSOLE SUMMARY
# ---------------------------------------------------------

def print_summary(summary):
    print()
    print("=" * 70)
    print("INVENTORY SUMMARY")
    print("=" * 70)

    total_files = 0

    for row in summary:
        total_files += row["file_count"]

        print()
        print(
            f"File type        : "
            f"{row['file_type'].upper()}"
        )
        print(
            f"File count       : "
            f"{row['file_count']}"
        )
        print(
            f"Total size (MB)  : "
            f"{row['total_size_mb']}"
        )
        print(
            f"Smallest (MB)    : "
            f"{row['smallest_file_mb']}"
        )
        print(
            f"Largest (MB)     : "
            f"{row['largest_file_mb']}"
        )
        print(
            f"Average (MB)     : "
            f"{row['average_file_mb']}"
        )
        print(
            f"Source folders   : "
            f"{row['source_folders']}"
        )

    print()
    print("-" * 70)
    print(f"TOTAL FILES: {total_files}")
    print("-" * 70)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    if (
        not S3_BUCKET_NAME
        or S3_BUCKET_NAME == "YOUR_BUCKET_NAME"
    ):
        print()
        print("ERROR:")
        print(
            "Please update S3_BUCKET_NAME "
            "inside documents_v2/config.py"
        )
        print()
        return

    try:
        s3_client = create_s3_client()

        records = list_s3_objects(
            s3_client=s3_client,
            bucket=S3_BUCKET_NAME,
            prefix=S3_DOCUMENT_PREFIX,
        )

        if not records:
            print()
            print(
                "No files were found under "
                f"{S3_DOCUMENT_PREFIX}"
            )
            return

        write_inventory_csv(
            records,
            INVENTORY_CSV,
        )

        summary = build_summary(records)

        write_summary_csv(
            summary,
            INVENTORY_SUMMARY_CSV,
        )

        print_summary(summary)

        print()
        print("Inventory completed successfully.")

    except NoCredentialsError:
        print()
        print("AWS credentials were not found.")
        print(
            "Configure AWS CLI / AWS SSO first "
            "and then run this script again."
        )

    except ProfileNotFound as exc:
        print()
        print("AWS profile was not found.")
        print(exc)

    except (BotoCoreError, ClientError) as exc:
        print()
        print("Unable to read the S3 inventory.")
        print(exc)

    except Exception as exc:
        print()
        print("Unexpected error:")
        print(type(exc).__name__, exc)
        raise


if __name__ == "__main__":
    main()