from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_FILE = BASE_DIR / "outputs" / "documents" / "document_catalog.xlsx"
OUTPUT_FILE = BASE_DIR / "outputs" / "documents" / "data_inventory.xlsx"

def main():
    df = pd.read_excel(INPUT_FILE)

    rows = []

    for _, row in df.iterrows():
        rows.append({
            "file_name": row["original_file_name"],
            "file_type": row["file_type"],
            "structured_or_unstructured": "Unstructured",
            "main_content": row["main_topic"],
            "future_platform_use": "PhD Library / AI",
            "current_status": "Auto processed"
        })

    pd.DataFrame(rows).to_excel(OUTPUT_FILE, index=False)
    print("data_inventory.xlsx created")

if __name__ == "__main__":
    main()