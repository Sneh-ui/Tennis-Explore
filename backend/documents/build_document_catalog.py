from pathlib import Path
import pandas as pd
import re
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_FILE = BASE_DIR / "outputs" / "documents" / "document_text_extraction.xlsx"
OUTPUT_FILE = BASE_DIR / "outputs" / "documents" / "document_catalog.xlsx"

TOPIC_MAP = {
    "wearable technology": ["wearable", "sensor", "catapult", "gps", "accelerometer", "gyroscope"],
    "stroke detection": ["stroke", "forehand", "backhand", "serve", "algorithm", "detect"],
    "movement analysis": ["movement", "running", "footwork", "dynamic", "load", "playerload"],
    "serve load monitoring": ["serve", "volume", "lumbar", "shoulder", "distribution"],
    "injury prevention": ["injury", "lumbar", "fracture", "risk", "fatigue", "recovery"],
    "periodisation": ["periodisation", "training", "competition", "tournament", "schedule", "weekly"],
    "competition scheduling": ["ranking", "matches", "junior", "professional", "tournament", "calendar"],
    "training drill analysis": ["drill", "technical", "match-play", "accuracy", "defensive", "points"]
}

STOPWORDS = {
    "the","and","for","with","this","that","from","were","have","been","their","they","using","used",
    "into","than","also","which","these","during","between","player","players","tennis","research",
    "study","paper","data","journal","sports","science","article","published","received","accepted"
}

COMMON_KEYWORDS = [
    "tennis",
    "wearable technology",
    "player load",
    "stroke detection",
    "movement analysis",
    "serve load",
    "injury prevention",
    "periodisation",
    "training monitoring",
    "performance analytics"
]

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_year(text):
    years = re.findall(r"\b(20\d{2}|19\d{2})\b", str(text))
    return years[0] if years else ""

def guess_title(original_file_name, text_preview):
    lines = [line.strip() for line in str(text_preview).split("\n") if line.strip()]
    for line in lines[:10]:
        if 20 <= len(line) <= 180:
            low = line.lower()
            if not any(x in low for x in ["doi", "copyright", "received", "accepted", "published", "license"]):
                return line
    return Path(original_file_name).stem

def guess_topic(text):
    cleaned = clean_text(text)
    scores = {}
    for topic, words in TOPIC_MAP.items():
        score = sum(cleaned.count(word) for word in words)
        scores[topic] = score
    best_topic = max(scores, key=scores.get)
    return best_topic if scores[best_topic] > 0 else "performance analytics"

def extract_keywords(text, top_n=3):
    cleaned = clean_text(text)
    words = cleaned.split()
    words = [w for w in words if len(w) > 4 and w not in STOPWORDS]
    freq = Counter(words)
    specific = [w for w, _ in freq.most_common(top_n)]
    final_keywords = COMMON_KEYWORDS[:5] + specific
    final_keywords = list(dict.fromkeys(final_keywords))[:8]
    return ", ".join(final_keywords)

def generate_questions(topic):
    return " | ".join([
        f"What does this document say about {topic}?",
        f"How can coaches use insights from {topic}?",
        f"Why is {topic} important in tennis?"
    ])

def main():
    df = pd.read_excel(INPUT_FILE)
    rows = []

    for _, row in df.iterrows():
        original_file_name = row["original_file_name"]
        file_type = row["file_type"]
        text_preview = row["text_preview"]

        title = guess_title(original_file_name, text_preview)
        year = extract_year(text_preview)
        topic = guess_topic(text_preview)
        keywords = extract_keywords(text_preview)
        questions = generate_questions(topic)

        rows.append({
            "original_file_name": original_file_name,
            "display_title": title,
            "file_type": file_type,
            "year": year,
            "main_topic": topic,
            "keywords": keywords,
            "can_answer_later": questions,
            "status": "auto_generated"
        })

    catalog_df = pd.DataFrame(rows)
    catalog_df.to_excel(OUTPUT_FILE, index=False)

    print("\n=== Document Catalog ===")
    print(catalog_df[["original_file_name", "main_topic", "keywords"]].to_string(index=False))
    print("\ndocument_catalog.xlsx created")

if __name__ == "__main__":
    main()