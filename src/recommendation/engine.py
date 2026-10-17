"""Recommendation strategies for the BookNooks catalog."""

from __future__ import annotations

import re
from collections.abc import Iterable


READER_PROFILES = {
    "adventure seeker": {
        "genres": "adventure action western survival",
        "moods": "adventurous hopeful suspenseful",
        "description": "Journeys, action, and high stakes",
    },
    "mystery solver": {
        "genres": "mystery crime detective thriller",
        "moods": "mysterious suspenseful",
        "description": "Puzzles, investigations, and hidden secrets",
    },
    "romance reader": {
        "genres": "romance love stories romantic fiction",
        "moods": "romantic hopeful",
        "description": "Relationships and love stories",
    },
    "curious explorer": {
        "genres": "biography memoir history science philosophy",
        "moods": "reflective hopeful",
        "description": "Real lives, ideas, and the world around us",
    },
}


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (value or "").casefold()))


def _field(book: dict, name: str) -> str:
    return str(book.get(name, "") or "")


def _genre_score(book: dict, wanted_genres: set[str]) -> float:
    if not wanted_genres:
        return 0.0
    book_genres = tokens(_field(book, "genres"))
    if not book_genres:
        return 0.0
    return len(wanted_genres & book_genres) / len(wanted_genres)


def _mood_score(book: dict, wanted_moods: set[str]) -> float:
    if not wanted_moods:
        return 0.0
    book_moods = tokens(_field(book, "mood_tags"))
    return len(wanted_moods & book_moods) / len(wanted_moods)


def recommend(
    books: Iterable[dict],
    genres: str = "",
    moods: str = "",
    query: str = "",
    strategy: str = "genre",
    limit: int = 5,
) -> list[dict]:
    """Rank books with the genre baseline or an explicitly experimental scorer."""
    catalog = list(books)
    if strategy not in {"genre", "tfidf", "mood"}:
        raise ValueError("strategy must be 'genre', 'tfidf', or 'mood'")
    if not catalog or limit <= 0:
        return []

    wanted_genres, wanted_moods = tokens(genres), tokens(moods)
    query_terms = " ".join(part for part in (genres, moods, query) if part).strip()
    tfidf_scores = [0.0] * len(catalog)
    if strategy == "tfidf" and query_terms:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError as error:
            raise RuntimeError("Install scikit-learn to use the TF-IDF strategy") from error

        documents = [
            " ".join(
                _field(book, key)
                for key in ("title", "author", "genres", "description")
            )
            for book in catalog
        ]
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform([query_terms, *documents])
        tfidf_scores = cosine_similarity(matrix[0:1], matrix[1:]).ravel().tolist()

    ranked = []
    for index, book in enumerate(catalog):
        genre = _genre_score(book, wanted_genres)
        mood = _mood_score(book, wanted_moods)
        if strategy == "genre":
            score = genre
        elif strategy == "tfidf":
            # Experimental hybrid; compare against genre-only before making claims.
            score = 0.5 * genre + 0.5 * tfidf_scores[index]
        else:
            # Experimental mood reranking; mood tags have not been human-validated.
            score = 0.7 * genre + 0.3 * mood
        ranked.append((score, genre, mood, index, book))

    ranked.sort(
        key=lambda item: (
            item[0], item[1], _field(item[4], "title").casefold()
        ),
        reverse=True,
    )
    results = []
    for score, genre, mood, _, book in ranked[:limit]:
        result = dict(book)
        result["recommendation_score"] = round(float(score), 4)
        result["genre_match"] = round(float(genre), 4)
        result["mood_match"] = round(float(mood), 4)
        result["matched_genres"] = [
            phrase.strip()
            for phrase in _field(book, "genres").split(";")
            if tokens(phrase) & wanted_genres
        ]
        result["strategy"] = strategy
        results.append(result)
    return results
