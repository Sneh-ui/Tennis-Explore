from ..data_loader import load_all_structured_data

# Load all datasets once
datasets = load_all_structured_data()

def get_all_match_data():
    import pandas as pd

    match_dfs = []

    for name, df in datasets.items():
        if "match" in name.lower():
            match_dfs.append(df)

    if not match_dfs:
        return None

    return pd.concat(match_dfs, ignore_index=True)


def get_rankings_data():
    for name, df in datasets.items():
        if "ranking" in name.lower():
            return df
    return None

import pandas as pd

def get_matches_by_surface(surface):
    df = get_all_match_data()

    if df is None:
        return {"error": "No match data found"}

    result = pd.DataFrame()

    for col in df.columns:
        if "surface" in col.lower():

            # 🔥 NORMALIZE surface column
            normalized = df[col].astype(str).str.lower().str.strip()

            normalized = normalized.replace({
                "h": "hard",
                "hard court": "hard",
                "g": "grass",
                "c": "clay"
            })

            # 🔥 Filter using normalized values
            temp = df[normalized.str.contains(surface.lower(), na=False)]

            result = pd.concat([result, temp])

    if result.empty:
        return []

    return result.head(20).to_dict(orient="records")


def get_win_loss_summary():
    df = get_all_match_data()

    if df is None:
        return {"error": "No match data found"}

    col = None
    for c in df.columns:
        if "win" in c.lower() or "loss" in c.lower():
            col = c
            break

    if col is None:
        return {"error": "No win/loss column found"}

    # Normalize values
    normalized = df[col].astype(str).str.lower().str.strip()

    normalized = normalized.replace({
        "w": "win",
        "win": "win",
        "won": "win",

        "l": "loss",
        "loss": "loss",
        "lost": "loss"
    })

    return normalized.value_counts().to_dict()


def get_tournaments():
    df = get_all_match_data()

    if df is None:
        return []

    col = None
    for c in df.columns:
        if "event" in c.lower() or "tournament" in c.lower():
            col = c
            break

    if col is None:
        return []

    return sorted(df[col].dropna().astype(str).unique().tolist())[:50]


def get_ranking_summary():
    df = get_rankings_data()

    if df is None:
        return {"error": "No ranking data found"}

    return df.head(20).to_dict(orient="records")