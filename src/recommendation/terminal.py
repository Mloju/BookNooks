"""Interactive terminal recommender for BookNooks."""

import argparse
import csv
from pathlib import Path

from src.recommendation.engine import READER_PROFILES, recommend


PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = PROJECT_DIR / "data" / "processed" / "books_sample_5000_with_moods.csv"


def load_catalog(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def prompt_choice(prompt: str, options: list[str]) -> str:
    while True:
        answer = input(prompt).strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        print(f"Enter a number from 1 to {len(options)}.")


def run(catalog_path: Path = DEFAULT_CATALOG, strategy: str = "genre") -> None:
    books = load_catalog(catalog_path)
    if not books:
        raise SystemExit(f"No books found in {catalog_path}")

    profile_names = list(READER_PROFILES)
    print("\nWelcome to BookNooks — let’s find your next read.\n")
    for number, name in enumerate(profile_names, 1):
        print(f"{number}. {name.title()} — {READER_PROFILES[name]['description']}")
    print(f"{len(profile_names) + 1}. Custom preferences")
    choice = prompt_choice("Choose a reader profile: ", [*profile_names, "custom"])

    if choice == "custom":
        default_genres, default_moods = "", ""
    else:
        default_genres = READER_PROFILES[choice]["genres"]
        default_moods = READER_PROFILES[choice]["moods"]
        print(f"\nProfile genres: {default_genres}")
        print(f"Profile moods: {default_moods}")

    genres = input("Genres you want (comma separated; Enter keeps profile): ").strip()
    moods = input("Moods you want (comma separated; Enter keeps profile): ").strip()
    query = input("Anything else? (themes, setting, or keywords; optional): ").strip()
    genres = genres or default_genres
    moods = moods or default_moods

    picks = recommend(books, genres=genres, moods=moods, query=query,
                      strategy=strategy, limit=5)
    print(f"\nYour five recommendations ({strategy} ranking):\n")
    for number, book in enumerate(picks, 1):
        print(f"{number}. {book.get('title') or 'Untitled'} — {book.get('author') or 'author unknown'}")
        genre_list = book.get("matched_genres") or []
        genre_summary = "; ".join(genre_list[:3]) or "No direct genre overlap"
        if len(genre_list) > 3:
            genre_summary += "; …"
        print(f"   Genres: {genre_summary}")
        if book.get("mood_tags"):
            print(f"   Moods: {book['mood_tags']}")
        print(f"   Source: {book.get('source_url') or 'not recorded'}")
    print("\nRanking note: genre-only is the baseline. TF-IDF and mood are experimental.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Find five books in the BookNooks catalog")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--strategy", choices=("genre", "tfidf", "mood"), default="genre")
    args = parser.parse_args()
    run(args.catalog, args.strategy)


if __name__ == "__main__":
    main()
