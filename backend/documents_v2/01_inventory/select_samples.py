import csv
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))


from config import (
    INVENTORY_CSV,
    REPRESENTATIVE_SAMPLE_CSV,
)


# =========================================================
# SETTINGS
# =========================================================

SUPPORTED_TYPES = {
    "pdf",
    "pptx",
}

SAMPLES_PER_TYPE = 4


# Percentile-style positions used for the normal
# production validation sample.
#
# We deliberately avoid 0% and 100% because those
# are extreme files rather than representative files.

SAMPLE_POSITIONS = [
    0.10,
    0.35,
    0.65,
    0.90,
]


# =========================================================
# LOAD INVENTORY
# =========================================================

def read_inventory(path):

    records = []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        for row in reader:

            row["size_mb"] = float(
                row["size_mb"]
            )

            row["size_bytes"] = int(
                row["size_bytes"]
            )

            records.append(row)

    return records


# =========================================================
# SAMPLE SELECTION
# =========================================================

def get_size_label(position):

    if position <= 0.15:
        return "small"

    if position <= 0.45:
        return "lower-medium"

    if position <= 0.75:
        return "upper-medium"

    return "large"


def select_representative_files(
    records,
    file_type,
):

    matching = [
        record
        for record in records
        if record[
            "file_type"
        ].lower() == file_type
    ]

    matching = sorted(
        matching,
        key=lambda item:
            item["size_mb"],
    )

    if not matching:
        return []

    selected = []

    total = len(matching)

    for position in SAMPLE_POSITIONS:

        index = round(
            position
            * (total - 1)
        )

        record = matching[
            index
        ].copy()

        record[
            "selection_reason"
        ] = (
            f"{get_size_label(position).capitalize()} "
            f"{file_type.upper()} selected "
            "from the production size distribution"
        )

        record[
            "sample_position"
        ] = position

        selected.append(record)

    return selected


# =========================================================
# EXTREME FILES
# =========================================================

def identify_extreme_files(
    records,
):

    extremes = []

    for file_type in sorted(
        SUPPORTED_TYPES
    ):

        matching = [
            record
            for record in records
            if record[
                "file_type"
            ].lower() == file_type
        ]

        if not matching:
            continue

        largest = max(
            matching,
            key=lambda item:
                item["size_mb"],
        ).copy()

        largest[
            "selection_reason"
        ] = (
            "Largest production "
            f"{file_type.upper()} "
            "reserved for stress testing"
        )

        extremes.append(largest)

    return extremes


# =========================================================
# SAVE REPRESENTATIVE SAMPLE
# =========================================================

def write_samples(
    samples,
    output_path,
):

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "sample_id",
        "file_type",
        "file_name",
        "size_mb",
        "source_folder",
        "s3_key",
        "selection_reason",
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for index, sample in enumerate(
            samples,
            start=1,
        ):

            writer.writerow(
                {
                    "sample_id":
                        f"SAMPLE-{index:02d}",

                    "file_type":
                        sample[
                            "file_type"
                        ],

                    "file_name":
                        sample[
                            "file_name"
                        ],

                    "size_mb":
                        sample[
                            "size_mb"
                        ],

                    "source_folder":
                        sample[
                            "source_folder"
                        ],

                    "s3_key":
                        sample[
                            "s3_key"
                        ],

                    "selection_reason":
                        sample[
                            "selection_reason"
                        ],
                }
            )


# =========================================================
# SAVE STRESS TEST FILES
# =========================================================

def write_extreme_files(
    files,
):

    output_path = (
        REPRESENTATIVE_SAMPLE_CSV
        .parent
        / "stress_test_files.csv"
    )

    fieldnames = [
        "file_type",
        "file_name",
        "size_mb",
        "source_folder",
        "s3_key",
        "selection_reason",
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for item in files:

            writer.writerow(
                {
                    key:
                        item.get(key)
                    for key
                    in fieldnames
                }
            )

    return output_path


# =========================================================
# DISPLAY
# =========================================================

def print_samples(samples):

    print()
    print("=" * 70)
    print(
        "REPRESENTATIVE PRODUCTION SAMPLE"
    )
    print("=" * 70)

    for index, sample in enumerate(
        samples,
        start=1,
    ):

        print()

        print(
            f"SAMPLE-{index:02d}"
        )

        print(
            f"Type   : "
            f"{sample['file_type'].upper()}"
        )

        print(
            f"Size   : "
            f"{sample['size_mb']:.3f} MB"
        )

        print(
            f"Folder : "
            f"{sample['source_folder']}"
        )

        print(
            f"Reason : "
            f"{sample['selection_reason']}"
        )

    print()

    print(
        f"Total selected: "
        f"{len(samples)}"
    )


def print_extremes(extremes):

    print()
    print("=" * 70)
    print(
        "DEFERRED STRESS-TEST FILES"
    )
    print("=" * 70)

    for item in extremes:

        print()

        print(
            f"Type : "
            f"{item['file_type'].upper()}"
        )

        print(
            f"Size : "
            f"{item['size_mb']:.3f} MB"
        )

        print(
            f"File : "
            f"{item['file_name']}"
        )

        print(
            "Status: deferred"
        )


# =========================================================
# MAIN
# =========================================================

def main():

    if not INVENTORY_CSV.exists():

        print(
            "Inventory file was not found:"
        )

        print(
            INVENTORY_CSV
        )

        return

    records = read_inventory(
        INVENTORY_CSV
    )

    samples = []

    for file_type in [
        "pdf",
        "pptx",
    ]:

        selected = (
            select_representative_files(
                records,
                file_type,
            )
        )

        samples.extend(
            selected
        )

    write_samples(
        samples,
        REPRESENTATIVE_SAMPLE_CSV,
    )

    extremes = identify_extreme_files(
        records
    )

    stress_path = write_extreme_files(
        extremes
    )

    print_samples(
        samples
    )

    print_extremes(
        extremes
    )

    print()
    print(
        "Representative sample saved to:"
    )

    print(
        REPRESENTATIVE_SAMPLE_CSV
    )

    print()
    print(
        "Stress-test file list saved to:"
    )

    print(
        stress_path
    )


if __name__ == "__main__":
    main()