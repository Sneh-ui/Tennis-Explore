import csv
import json
from pathlib import Path
from collections import Counter


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


def get_resource_id(data, chunk_file):
    """
    Production chunk files use an output_stem like:

    0063081dec58b2fc_free-comm-posters-thurs-pm

    The first section is the stable resource_id.
    """

    output_stem = str(
        data.get("output_stem", "")
    ).strip()

    if output_stem:
        return output_stem.split("_", 1)[0]

    # Fallback to filename if output_stem is absent.
    filename = chunk_file.name

    return filename.split("_", 1)[0]


def main():

    print("=" * 70)
    print("TENNIS EXPLORE - CHUNK DATABASE VALIDATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Load manifest
    # --------------------------------------------------------

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        manifest_rows = list(csv.DictReader(f))

    manifest_by_resource = {
        row["resource_id"].strip(): row
        for row in manifest_rows
        if row.get("resource_id")
    }

    valid_resource_ids = set(
        manifest_by_resource.keys()
    )

    print(
        f"\nDocument records available : "
        f"{len(valid_resource_ids)}"
    )

    # --------------------------------------------------------
    # Find chunk files
    # --------------------------------------------------------

    chunk_files = sorted(
        CHUNKS_DIR.glob("*_chunks.json")
    )

    print(
        f"Chunk JSON files found     : "
        f"{len(chunk_files)}"
    )

    total_chunks = 0
    valid_chunks = 0
    invalid_chunks = 0

    invalid_samples = []

    seen_database_keys = set()
    duplicate_database_keys = []

    chunks_per_document = Counter()

    chunk_file_count_mismatches = []

    # --------------------------------------------------------
    # Validate files
    # --------------------------------------------------------

    for chunk_file in chunk_files:

        try:

            with chunk_file.open(
                "r",
                encoding="utf-8",
            ) as f:
                data = json.load(f)

        except Exception as exc:

            invalid_samples.append({
                "file": chunk_file.name,
                "errors": [
                    f"Could not read JSON: {exc}"
                ],
            })

            continue

        if not isinstance(data, dict):

            invalid_samples.append({
                "file": chunk_file.name,
                "errors": [
                    "Top-level JSON is not an object"
                ],
            })

            continue

        resource_id = get_resource_id(
            data,
            chunk_file,
        )

        chunks = data.get("chunks", [])

        if not isinstance(chunks, list):

            invalid_samples.append({
                "file": chunk_file.name,
                "errors": [
                    "'chunks' is not a list"
                ],
            })

            continue

        # ----------------------------------------------------
        # Compare JSON total_chunks against actual list
        # ----------------------------------------------------

        declared_total = data.get(
            "total_chunks"
        )

        if (
            declared_total is not None
            and declared_total != len(chunks)
        ):
            chunk_file_count_mismatches.append(
                {
                    "file": chunk_file.name,
                    "declared": declared_total,
                    "actual": len(chunks),
                }
            )

        # ----------------------------------------------------
        # Validate chunks
        # ----------------------------------------------------

        for chunk in chunks:

            total_chunks += 1

            errors = []

            source_chunk_id = str(
                chunk.get("chunk_id", "")
            ).strip()

            chunk_index = chunk.get(
                "chunk_index"
            )

            chunk_text = str(
                chunk.get("text", "")
            ).strip()

            if not resource_id:
                errors.append(
                    "missing resource_id"
                )

            elif resource_id not in valid_resource_ids:
                errors.append(
                    "resource_id not found in manifest"
                )

            if not source_chunk_id:
                errors.append(
                    "missing source chunk_id"
                )

            if chunk_index is None:
                errors.append(
                    "missing chunk_index"
                )

            if not chunk_text:
                errors.append(
                    "missing chunk text"
                )

            # Database uniqueness rule:
            #
            # UNIQUE(document_id, source_chunk_id)

            if resource_id and source_chunk_id:

                database_key = (
                    resource_id,
                    source_chunk_id,
                )

                if database_key in seen_database_keys:

                    duplicate_database_keys.append(
                        database_key
                    )

                else:

                    seen_database_keys.add(
                        database_key
                    )

            if errors:

                invalid_chunks += 1

                if len(invalid_samples) < 20:

                    invalid_samples.append({
                        "file": chunk_file.name,
                        "resource_id": resource_id,
                        "source_chunk_id": source_chunk_id,
                        "chunk_index": chunk_index,
                        "errors": errors,
                    })

            else:

                valid_chunks += 1

                chunks_per_document[
                    resource_id
                ] += 1

    # --------------------------------------------------------
    # Documents without chunks
    # --------------------------------------------------------

    documents_without_chunks = (
        valid_resource_ids
        - set(chunks_per_document.keys())
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("VALIDATION SUMMARY")
    print("-" * 70)

    print(
        f"Total chunks             : {total_chunks}"
    )

    print(
        f"Valid chunks             : {valid_chunks}"
    )

    print(
        f"Invalid chunks           : {invalid_chunks}"
    )

    print(
        f"Duplicate database keys  : "
        f"{len(duplicate_database_keys)}"
    )

    print(
        f"Chunk count mismatches   : "
        f"{len(chunk_file_count_mismatches)}"
    )

    print(
        f"Documents with chunks    : "
        f"{len(chunks_per_document)}"
    )

    print(
        f"Documents without chunks : "
        f"{len(documents_without_chunks)}"
    )

    # --------------------------------------------------------
    # Invalid samples
    # --------------------------------------------------------

    if invalid_samples:

        print("\n" + "-" * 70)
        print("SAMPLE INVALID RECORDS")
        print("-" * 70)

        for item in invalid_samples[:20]:

            print(
                f"\nFile: {item.get('file')}"
            )

            if item.get("resource_id"):
                print(
                    f"Resource ID: "
                    f"{item.get('resource_id')}"
                )

            if item.get("source_chunk_id"):
                print(
                    f"Chunk ID: "
                    f"{item.get('source_chunk_id')}"
                )

            for error in item.get(
                "errors",
                []
            ):
                print(f"  - {error}")

    # --------------------------------------------------------
    # Duplicate keys
    # --------------------------------------------------------

    if duplicate_database_keys:

        print("\n" + "-" * 70)
        print("SAMPLE DUPLICATE DATABASE KEYS")
        print("-" * 70)

        for key in duplicate_database_keys[:20]:
            print(key)

    # --------------------------------------------------------
    # Count mismatches
    # --------------------------------------------------------

    if chunk_file_count_mismatches:

        print("\n" + "-" * 70)
        print("SAMPLE CHUNK COUNT MISMATCHES")
        print("-" * 70)

        for item in chunk_file_count_mismatches[:20]:

            print(
                f"{item['file']}: "
                f"declared={item['declared']}, "
                f"actual={item['actual']}"
            )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    print("\n" + "=" * 70)

    if (
        invalid_chunks == 0
        and len(duplicate_database_keys) == 0
        and len(chunk_file_count_mismatches) == 0
        and len(invalid_samples) == 0
    ):

        print(
            "CHUNK VALIDATION PASSED - chunks are "
            "ready for database mapping."
        )

    else:

        print(
            "CHUNK VALIDATION FOUND ISSUES - "
            "review before database loading."
        )

    print("=" * 70)


if __name__ == "__main__":
    main()