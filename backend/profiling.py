from pathlib import Path
import pandas as pd
from data_loader import load_match_data, load_rankings_data

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "csv_profile_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def profile_dataframe(df: pd.DataFrame, name: str):
    print(f"\n===== {name} =====")
    print("Shape (rows, columns):", df.shape)

    print("\nColumn names:")
    print(list(df.columns))

    print("\nMissing values:")
    print(df.isnull().sum())

    print("\nFirst 5 rows:")
    print(df.head())

    summary = pd.DataFrame({
        "column_name": df.columns,
        "dtype": [str(df[col].dtype) for col in df.columns],
        "missing_values": [df[col].isnull().sum() for col in df.columns],
        "sample_value": [
            str(df[col].dropna().iloc[0]) if not df[col].dropna().empty else ""
            for col in df.columns
        ]
    })

    summary.to_excel(OUTPUT_DIR / f"{name}_column_summary.xlsx", index=False)

def basic_match_analysis(df: pd.DataFrame, name: str):
    print(f"\n===== Basic Match Analysis: {name} =====")

    if "surface_category" in df.columns:
        print("\nMatches by surface:")
        print(df["surface_category"].value_counts(dropna=False))

    if "win_loss_status" in df.columns:
        print("\nWins vs Losses:")
        print(df["win_loss_status"].value_counts(dropna=False))

    if "event_name" in df.columns:
        print("\nTop tournaments:")
        print(df["event_name"].value_counts().head(10))

def basic_rankings_analysis(df: pd.DataFrame):
    print("\n===== Basic Rankings Analysis =====")

    if "player_name" in df.columns:
        print("\nUnique players:")
        print(df["player_name"].nunique())

    if "ranking" in df.columns:
        print("\nRanking statistics:")
        print(df["ranking"].describe())

def main():
    match1, match2 = load_match_data()
    rankings = load_rankings_data()

    profile_dataframe(match1, "match_data_1")
    basic_match_analysis(match1, "match_data_1")

    profile_dataframe(match2, "match_data_2")
    basic_match_analysis(match2, "match_data_2")

    profile_dataframe(rankings, "rankings")
    basic_rankings_analysis(rankings)

if __name__ == "__main__":
    main()