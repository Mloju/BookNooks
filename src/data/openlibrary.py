"""Reusable Open Library collection and quality reporting functions."""

from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

BASE_URL = "https://openlibrary.org"
MIN_DESCRIPTION_WORDS = 50
USER_AGENT = "BookNookCapstone/1.0"
FIELDS = [
    "book_id", "title", "author", "publication_year", "description",
    "description_word_count", "genres", "source_url", "rights_notes",
    "details_retrieved",
]


def fetch_search_results(query: str = "subject:fantasy", limit: int = 100) -> dict:
    response = requests.get(
        f"{BASE_URL}/search.json",
        params={"q": query, "limit": limit,
                "fields": "key,title,author_name,first_publish_year,subject"},
        headers={"User-Agent": USER_AGENT}, timeout=30,
    )
    response.raise_for_status()
    return response.json()


def collect_records(
    search_data: dict,
    raw_details_dir: Path,
    pause_seconds: float = 1.0,
    get: Callable = requests.get,
) -> list[dict]:
    """Fetch details and return one saved-data row per valid search work ID."""
    raw_details_dir.mkdir(parents=True, exist_ok=True)
    books = []
    for item in search_data.get("docs", []):
        work_id = item.get("key")
        if not work_id:
            continue
        description = ""
        detail_retrieved = False
        try:
            response = get(f"{BASE_URL}{work_id}.json",
                           headers={"User-Agent": USER_AGENT}, timeout=30)
            response.raise_for_status()
            details = response.json()
            detail_retrieved = True
            raw_file = raw_details_dir / f"{work_id.split('/')[-1]}.json"
            raw_file.write_text(json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
            description = details.get("description", "")
            if isinstance(description, dict):
                description = description.get("value", "")
            if not isinstance(description, str):
                description = ""
        except (requests.RequestException, ValueError) as error:
            print(f"Could not retrieve details for {work_id}: {error}")

        subjects = item.get("subject") or []
        if not isinstance(subjects, list):
            subjects = []
        books.append({
            "book_id": work_id,
            "title": item.get("title") or "",
            "author": "; ".join(item.get("author_name") or []),
            "publication_year": item.get("first_publish_year") or "",
            "description": description.strip(),
            "description_word_count": len(description.split()),
            "genres": "; ".join(subjects),
            "source_url": f"{BASE_URL}{work_id}",
            "rights_notes": "Verify applicable source terms and excerpt permissions before reuse.",
            "details_retrieved": detail_retrieved,
        })
        if pause_seconds:
            time.sleep(pause_seconds)
    return books


def write_collection(
    books: list[dict], search_data: dict, raw_search_file: Path,
    raw_details_dir: Path, processed_dir: Path, requested: int,
    query: str = "subject:fantasy",
) -> tuple[Path, Path, dict]:
    """Persist source and processed files, then report counts on saved rows."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_search_file.write_text(json.dumps(search_data, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_path = processed_dir / f"books_sample_{timestamp}.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(books)

    total = len(books)
    descriptions = sum(int(book["description_word_count"]) >= MIN_DESCRIPTION_WORDS for book in books)
    genres = sum(bool(book["genres"].strip()) for book in books)
    all_three = sum(int(book["description_word_count"]) >= MIN_DESCRIPTION_WORDS
                    and bool(book["genres"].strip()) for book in books)
    percent = lambda count: round(100 * count / total, 2) if total else 0.0
    summary = {
        "collection_date_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Open Library API", "query": query,
        "requested_sample_size": requested,
        "search_results_returned": len(search_data.get("docs", [])),
        "saved_records": total,
        "unique_saved_book_ids": len({book["book_id"] for book in books}),
        "target_saved_percent": round(100 * total / requested, 2) if requested else None,
        "description_word_threshold": MIN_DESCRIPTION_WORDS,
        "usable_descriptions": descriptions,
        "usable_descriptions_percent": percent(descriptions),
        "records_with_genres": genres,
        "records_with_genres_percent": percent(genres),
        "records_with_mood_derivable": descriptions,
        "records_with_mood_derivable_percent": percent(descriptions),
        "records_with_all_three": all_three,
        "records_with_all_three_percent": percent(all_three),
        "source_url_records": sum(bool(book["source_url"]) for book in books),
        "rights_notes_records": sum(bool(book["rights_notes"]) for book in books),
        "note": "Mood derivability means description length meets threshold; tags are heuristic and unvalidated.",
        "raw_search_file": str(raw_search_file),
        "raw_details_directory": str(raw_details_dir),
        "processed_csv": str(csv_path),
    }
    summary_path = processed_dir / f"quality_summary_{timestamp}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return csv_path, summary_path, summary
