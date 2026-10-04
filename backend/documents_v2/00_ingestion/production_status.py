import csv
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

PRODUCTION_DIR = (
    DOCUMENTS_V2_DIR
    / "outputs"
    / "production"
)

MANIFEST_PATH = (
    PRODUCTION_DIR
    / "processing_manifest.csv"
)

PLAN_PATH = (
    PRODUCTION_DIR
    / "s3_ingestion_plan.csv"
)


def load_csv(path):
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def main():

    manifest = load_csv(
        MANIFEST_PATH
    )

    plan = load_csv(
        PLAN_PATH
    )

    processed = 0
    failed = 0
    needs_ocr = 0
    invalid_pptx = 0

    pdf_processed = 0
    pptx_processed = 0

    total_chunks = 0

    for row in manifest:

        status = row.get(
            "processing_status",
            "",
        )

        extraction = row.get(
            "extraction_status",
            "",
        )

        file_type = row.get(
            "file_type",
            "",
        )

        if status == "processed":
            processed += 1

            if file_type == "pdf":
                pdf_processed += 1

            elif file_type == "pptx":
                pptx_processed += 1

        elif status == "failed":
            failed += 1

        if extraction == "needs_ocr":
            needs_ocr += 1

        if extraction == "invalid_pptx":
            invalid_pptx += 1

        try:
            total_chunks += int(
                row.get(
                    "chunk_count",
                    0,
                )
                or 0
            )
        except ValueError:
            pass

    ready_total = sum(
        1
        for row in plan
        if row.get("status") == "ready"
    )

    completed_keys = {
        row.get("s3_key")
        for row in manifest
        if row.get(
            "processing_status"
        )
        in {
            "processed",
            "failed",
        }
    }

    remaining = sum(
        1
        for row in plan
        if (
            row.get("status")
            == "ready"
            and row.get("s3_key")
            not in completed_keys
        )
    )

    print()
    print("=" * 72)
    print(
        "TENNIS EXPLORE - "
        "PRODUCTION INGESTION STATUS"
    )
    print("=" * 72)

    print()
    print(
        f"Ready S3 objects      : "
        f"{ready_total}"
    )

    print(
        f"Manifest records      : "
        f"{len(manifest)}"
    )

    print(
        f"Processed             : "
        f"{processed}"
    )

    print(
        f"Failed                : "
        f"{failed}"
    )

    print(
        f"Needs OCR             : "
        f"{needs_ocr}"
    )

    print(
        f"Invalid PPTX          : "
        f"{invalid_pptx}"
    )

    print()
    print(
        f"PDF processed         : "
        f"{pdf_processed}"
    )

    print(
        f"PPTX processed        : "
        f"{pptx_processed}"
    )

    print()
    print(
        f"Total chunks created  : "
        f"{total_chunks}"
    )

    print(
        f"Remaining ready files : "
        f"{remaining}"
    )

    if ready_total:
        completed = (
            processed + failed
        )

        percentage = (
            completed
            / ready_total
            * 100
        )

        print(
            f"Completion            : "
            f"{percentage:.1f}%"
        )

    print()


if __name__ == "__main__":
    main()