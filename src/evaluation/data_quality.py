"""Recompute saved-record and quality counts from a processed book CSV."""

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]


def summarize(path: Path, requested: int = 100) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as file:
        books = list(csv.DictReader(file))
    saved = len(books)
    unique_ids = len({row.get("book_id", "").strip() for row in books
                      if row.get("book_id", "").strip()})
    usable = sum(int(row.get("description_word_count", 0) or 0) >= 50 for row in books)
    titled = sum(bool(row.get("title", "").strip()) for row in books)
    with_genres = sum(bool(row.get("genres", "").strip()) for row in books)
    source_recorded = sum(bool(row.get("source_url", "").strip()) for row in books)
    rights_recorded = sum(bool(row.get("rights_notes", "").strip()) for row in books)

    def pct(count: int) -> float:
        return round(100 * count / saved, 2) if saved else 0.0

    return {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": path.relative_to(PROJECT_DIR).as_posix(),
        "targeted_books": requested,
        "saved_records": saved,
        "unique_book_ids": unique_ids,
        "duplicate_book_id_rows": saved - unique_ids,
        "records_with_title": titled,
        "records_with_title_percent": pct(titled),
        "target_saved_percent": round(100 * saved / requested, 2) if requested else None,
        "description_threshold_words": 50,
        "usable_descriptions": usable,
        "usable_descriptions_percent": pct(usable),
        "records_with_genres": with_genres,
        "records_with_genres_percent": pct(with_genres),
        "records_with_source_url": source_recorded,
        "records_with_rights_notes": rights_recorded,
        "records_with_mood_tags": sum(bool(r.get("mood_tags", "").strip()) for r in books),
        "note": "Mood tags are heuristic and have not been human-validated yet.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path, nargs="?", default=PROJECT_DIR / "data/processed/books_sample_5000_with_moods.csv")
    parser.add_argument("--target", type=int, default=5000)
    parser.add_argument("--output", type=Path, default=PROJECT_DIR / "results/metrics/data_quality.json")
    args = parser.parse_args()
    report = summarize(args.csv.resolve(), args.target)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved report: {args.output}")


if __name__ == "__main__":
    main()
