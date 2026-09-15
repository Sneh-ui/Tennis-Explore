import csv
import sys
from pathlib import Path

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)


CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))


from config import (
    S3_BUCKET_NAME,
    REPRESENTATIVE_SAMPLE_CSV,
    PDF_TEST_DIR,
    PPTX_TEST_DIR,
)


# =========================================================
# SETTINGS
# =========================================================

# Safety limit for normal automatic sample downloads.
#
# Files larger than this will not be downloaded
# automatically at this stage.

MAX_SAMPLE_SIZE_MB = 150


# =========================================================
# LOAD SAMPLE CSV
# =========================================================

def load_samples(path):

    samples = []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as csv_file:

        reader = csv.DictReader(
            csv_file
        )

        for row in reader:

            row["size_mb"] = float(
                row["size_mb"]
            )

            samples.append(row)

    return samples


# =========================================================
# DESTINATION
# =========================================================

def get_destination(sample):

    file_type = (
        sample[
            "file_type"
        ].lower()
    )

    if file_type == "pdf":

        return (
            PDF_TEST_DIR
            / sample["file_name"]
        )

    if file_type == "pptx":

        return (
            PPTX_TEST_DIR
            / sample["file_name"]
        )

    return None


# =========================================================
# DOWNLOAD
# =========================================================

def download_sample(
    s3_client,
    sample,
):

    destination = (
        get_destination(
            sample
        )
    )

    if destination is None:

        print(
            f"Skipping unsupported type: "
            f"{sample['file_type']}"
        )

        return "skipped"

    if (
        sample["size_mb"]
        > MAX_SAMPLE_SIZE_MB
    ):

        print()
        print(
            f"SKIPPED LARGE FILE: "
            f"{sample['file_name']}"
        )

        print(
            f"Size: "
            f"{sample['size_mb']:.3f} MB"
        )

        print(
            f"Limit: "
            f"{MAX_SAMPLE_SIZE_MB} MB"
        )

        return "large_skipped"

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if destination.exists():

        print()
        print(
            f"Already exists: "
            f"{destination.name}"
        )

        return "existing"

    print()
    print(
        f"Downloading: "
        f"{sample['file_name']}"
    )

    print(
        f"Size: "
        f"{sample['size_mb']:.3f} MB"
    )

    print(
        f"S3 key: "
        f"{sample['s3_key']}"
    )

    try:

        s3_client.download_file(
            S3_BUCKET_NAME,
            sample["s3_key"],
            str(destination),
        )

    except (
        ClientError,
        BotoCoreError,
    ) as exc:

        print(
            f"DOWNLOAD FAILED: "
            f"{exc}"
        )

        return "failed"

    print(
        f"Saved: {destination}"
    )

    return "downloaded"


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 70)
    print(
        "TENNIS EXPLORE - "
        "S3 SAMPLE DOWNLOAD"
    )
    print("=" * 70)

    if not REPRESENTATIVE_SAMPLE_CSV.exists():

        print(
            "Representative sample CSV "
            "does not exist."
        )

        print(
            "Run select_samples.py first."
        )

        return

    samples = load_samples(
        REPRESENTATIVE_SAMPLE_CSV
    )

    print(
        f"Samples found: "
        f"{len(samples)}"
    )

    s3_client = boto3.client(
        "s3"
    )

    counts = {
        "downloaded": 0,
        "existing": 0,
        "large_skipped": 0,
        "failed": 0,
        "skipped": 0,
    }

    for sample in samples:

        result = download_sample(
            s3_client,
            sample,
        )

        counts[result] += 1

    print()
    print("=" * 70)
    print(
        "DOWNLOAD SUMMARY"
    )
    print("=" * 70)

    print(
        f"Downloaded       : "
        f"{counts['downloaded']}"
    )

    print(
        f"Already existing : "
        f"{counts['existing']}"
    )

    print(
        f"Large skipped    : "
        f"{counts['large_skipped']}"
    )

    print(
        f"Failed           : "
        f"{counts['failed']}"
    )

    print(
        f"Other skipped    : "
        f"{counts['skipped']}"
    )


if __name__ == "__main__":
    main()