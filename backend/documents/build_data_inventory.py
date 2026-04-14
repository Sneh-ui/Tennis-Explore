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
            "future_platform_use": "PhD Library / AI Retrieval",
            "current_status": "Auto processed"
        })

    inventory_df = pd.DataFrame(rows)
    inventory_df.to_excel(OUTPUT_FILE, index=False)

    print("\n=== Data Inventory ===")
    print(inventory_df.to_string(index=False))
    print("\ndata_inventory.xlsx created")

if __name__ == "__main__":
    main()