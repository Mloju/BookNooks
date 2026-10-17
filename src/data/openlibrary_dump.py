"""Fast, early-stop importer for unique works from an Open Library works dump.

This importer does not scan for subject balance or read the authors dump. It
streams records in source order and stops as soon as it has the requested
number of valid, unique works. Existing output files are protected by default.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from src.features.mood_tagger import tag_mood

PROJECT_DIR = Path(__file__).resolve().parents[2]
BASE_URL = "https://openlibrary.org"
RIGHTS_NOTE = "Open Library metadata record; verify applicable source terms before reuse."
FIELDS = [
    "book_id", "title", "author", "publication_year", "description",
    "description_word_count", "genres", "mood_tags", "source_url",
    "rights_notes", "details_retrieved", "catalog_category", "author_ids",
]


def stream_works(dump_path: Path) -> Iterator[tuple[str, dict]]:
    """Yield (work key, decoded record) from a tab-separated gzip dump."""
    with gzip.open(dump_path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            parts = line.rstrip("\n").split("\t", 2)
            if len(parts) != 3:
                continue
            key, _revision, payload = parts
            if not key.startswith("/works/"):
                continue
            try:
                record = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(record, dict):
                yield key, record


def _text(value: object) -> str:
    if isinstance(value, dict):
        value = value.get("value", "")
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    return value.strip() if isinstance(value, str) else ""


def _author_ids(record: dict) -> list[str]:
    result = []
    for author in record.get("authors", []) or []:
        if isinstance(author, dict):
            key = author.get("author", {}).get("key", "")
            if key.startswith("/authors/"):
                result.append(key.rsplit("/", 1)[-1])
    return result


def _row(work_id: str, record: dict) -> dict | None:
    title = _text(record.get("title"))
    if not title:
        return None
    description = _text(record.get("description"))
    subjects = record.get("subjects") or []
    if not isinstance(subjects, list):
        subjects = []
    genres = "; ".join(dict.fromkeys(
        str(subject).strip() for subject in subjects if str(subject).strip()
    ))
    year = record.get("first_publish_date", "")
    year = year[:4] if isinstance(year, str) and len(year) >= 4 else ""
    authors = _author_ids(record)
    return {
        "book_id": work_id,
        "title": title,
        "author": "",  # Author names require a separate, expensive authors-dump pass.
        "publication_year": year,
        "description": description,
        "description_word_count": len(description.split()),
        "genres": genres,
        "mood_tags": tag_mood(description),
        "source_url": f"{BASE_URL}{work_id}",
        "rights_notes": RIGHTS_NOTE,
        "details_retrieved": True,
        "catalog_category": "",
        "author_ids": "; ".join(authors),
    }


def import_catalog(
    dump_path: Path,
    output_path: Path,
    target: int = 5000,
    overwrite: bool = False,
) -> dict:
    """Write up to target valid unique work rows, stopping at the target."""
    if target < 1:
        raise ValueError("target must be at least 1")
    if not dump_path.is_file():
        raise FileNotFoundError(dump_path)
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Refusing to replace existing catalog: {output_path}. Use --overwrite explicitly."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    saved = 0
    output_path = output_path.resolve()
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        with temporary_path.open("w", newline="", encoding="utf-8-sig") as output:
            writer = csv.DictWriter(output, fieldnames=FIELDS)
            writer.writeheader()
            for work_id, record in stream_works(dump_path):
                if work_id in seen:
                    continue
                row = _row(work_id, record)
                if row is None:
                    continue
                seen.add(work_id)
                writer.writerow(row)
                saved += 1
                if saved >= target:
                    break
        if saved != target:
            raise RuntimeError(f"Dump yielded {saved} valid unique works; target was {target}.")
        if output_path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to replace existing catalog: {output_path}")
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Open Library works dump",
        "source_dump": dump_path.name,
        "source_url": "https://openlibrary.org/data/ol_dump_works_latest.txt.gz",
        "target_records": target,
        "saved_records": saved,
        "unique_work_ids": len(seen),
        "validity_rule": "non-empty title and unique /works/ key",
        "collection_method": "stream source order and stop at target; no category classification",
        "catalog": output_path.relative_to(PROJECT_DIR).as_posix()
        if output_path.is_relative_to(PROJECT_DIR) else str(output_path),
        "source_and_rights_fields": "source_url and rights_notes retained in each row",
    }
    report_path = output_path.with_suffix(".json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dump", nargs="?", type=Path,
        default=PROJECT_DIR / "data/raw/ol_dump_works_latest.txt.gz",
    )
    parser.add_argument("--target", type=int, default=5000)
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT_DIR / "data/processed/books_sample_5000_fast_with_moods.csv",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    report = import_catalog(args.dump.resolve(), args.output.resolve(), args.target, args.overwrite)
    print(json.dumps(report, indent=2))
    print(f"Report saved: {args.output.with_suffix('.json')}")


if __name__ == "__main__":
    main()
