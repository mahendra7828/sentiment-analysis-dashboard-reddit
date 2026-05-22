from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.reddit_client import RedditComment


POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05

STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "been",
    "being",
    "could",
    "does",
    "doing",
    "from",
    "have",
    "just",
    "like",
    "more",
    "much",
    "only",
    "over",
    "really",
    "should",
    "some",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "very",
    "were",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
    "your",
}

COLUMNS = [
    "id",
    "author",
    "body",
    "comment_score",
    "permalink",
    "created_at",
    "positive",
    "neutral",
    "negative",
    "compound",
    "sentiment",
]


def analyze_comments(comments: Iterable[RedditComment]) -> pd.DataFrame:
    analyzer = SentimentIntensityAnalyzer()
    rows = []

    for comment in comments:
        scores = analyzer.polarity_scores(comment.body)
        compound = scores["compound"]
        rows.append(
            {
                "id": comment.id,
                "author": comment.author,
                "body": comment.body,
                "comment_score": comment.score,
                "permalink": comment.permalink,
                "created_at": comment.created_at,
                "positive": scores["pos"],
                "neutral": scores["neu"],
                "negative": scores["neg"],
                "compound": compound,
                "sentiment": classify_sentiment(compound),
            }
        )

    return pd.DataFrame(rows, columns=COLUMNS)


def classify_sentiment(compound: float) -> str:
    if compound >= POSITIVE_THRESHOLD:
        return "Positive"
    if compound <= NEGATIVE_THRESHOLD:
        return "Negative"
    return "Neutral"


def summarize_sentiment(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {
            "total": 0,
            "positive_pct": 0.0,
            "negative_pct": 0.0,
            "neutral_pct": 0.0,
            "avg_compound": 0.0,
        }

    total = len(df)
    counts = df["sentiment"].value_counts()
    positive_count = int(counts.get("Positive", 0))
    negative_count = int(counts.get("Negative", 0))
    neutral_count = int(counts.get("Neutral", 0))

    return {
        "total": int(total),
        "positive_pct": round((positive_count / total) * 100, 1),
        "negative_pct": round((negative_count / total) * 100, 1),
        "neutral_pct": round((neutral_count / total) * 100, 1),
        "avg_compound": round(float(df["compound"].mean()), 3),
    }


def common_words(df: pd.DataFrame, sentiment: str | None = None, limit: int = 15) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["word", "count"])

    source = df
    if sentiment:
        source = source[source["sentiment"] == sentiment]

    words: list[str] = []
    for text in source["body"].dropna():
        tokens = re.findall(r"[A-Za-z][A-Za-z']{2,}", text.lower())
        words.extend(token for token in tokens if token not in STOPWORDS)

    return pd.DataFrame(Counter(words).most_common(limit), columns=["word", "count"])
