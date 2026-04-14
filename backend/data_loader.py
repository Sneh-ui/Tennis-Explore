from pathlib import Path
import pandas as pd
import json

BASE_DIR = Path(__file__).resolve().parent.parent
STRUCTURED_DIR = BASE_DIR / "data" / "structured"

def load_all_structured_data():
    all_data = {}

    for file in STRUCTURED_DIR.iterdir():
        try:
            # CSV
            if file.suffix == ".csv":
                df = pd.read_csv(file)

            # Excel
            elif file.suffix in [".xlsx", ".xls"]:
                df = pd.read_excel(file)

            # JSON
            elif file.suffix == ".json":
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, list):
                    df = pd.DataFrame(data)

                elif isinstance(data, dict):
                    df = pd.json_normalize(data)

                else:
                    print(f"Unsupported JSON format: {file.name}")
                    continue

            else:
                continue

            # store using file name
            all_data[file.stem] = df

        except Exception as e:
            print(f"Error loading {file.name}: {e}")

    return all_data