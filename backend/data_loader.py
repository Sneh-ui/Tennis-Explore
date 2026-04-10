from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
STRUCTURED_DIR = BASE_DIR / "data" / "structured"

def load_match_data():
    path1 = STRUCTURED_DIR / "match-data-example.csv"
    path2 = STRUCTURED_DIR / "match-data-example[74].csv"

    df1 = pd.read_csv(path1)
    df2 = pd.read_csv(path2)

    return df1, df2

def load_rankings_data():
    path = STRUCTURED_DIR / "rankings.csv"
    df = pd.read_csv(path)
    return df