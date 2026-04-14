from pathlib import Path
import pandas as pd
from data_loader import load_all_structured_data

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "csv_profile_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def profile_dataframe(df: pd.DataFrame, name: str):
    print(f"\n===== {name} =====")

    print("Shape:", df.shape)

    print("\nColumns:")
    print(list(df.columns))

    print("\nMissing values:")
    print(df.isnull().sum())

    print("\nSample rows:")
    print(df.head())

    summary = pd.DataFrame({
        "column_name": df.columns,
        "dtype": [str(df[col].dtype) for col in df.columns],
        "missing_values": [df[col].isnull().sum() for col in df.columns],
    })

    summary.to_excel(OUTPUT_DIR / f"{name}_summary.xlsx", index=False)


def smart_basic_analysis(df: pd.DataFrame):
    print("\n--- Smart Analysis ---")

    for col in df.columns:
        try:
            # Text columns
            if df[col].dtype == "object":
                print(f"\nTop values in {col}:")
                print(df[col].value_counts().head(5))

            # Numeric columns
            else:
                print(f"\nStats for {col}:")
                print(df[col].describe())

        except:
            print(f"Skipping column {col}")


def main():
    datasets = load_all_structured_data()

    for name, df in datasets.items():
        profile_dataframe(df, name)
        smart_basic_analysis(df)


if __name__ == "__main__":
    main()