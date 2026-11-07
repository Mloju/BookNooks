"""Prepare blinded, paired human-rating sheets for ranking methods."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from src.recommendation.engine import READER_PROFILES, recommend

PROJECT_DIR = Path(__file__).resolve().parents[2]
METHODS = ("genre", "tfidf", "mood", "guided")


def prepare(input_path: Path, output_dir: Path, per_group: int = 3, seed: int = 20261023) -> dict:
    with input_path.open(encoding="utf-8-sig", newline="") as f:
        books = list(csv.DictReader(f))
    if not books:
        raise ValueError(f"No books found in {input_path}")
    stratified: dict[tuple[str, str, str], list[dict]] = {}
    key_rows = []
    for profile_name, profile in READER_PROFILES.items():
        for method in METHODS:
            ranked = recommend(books, profile["genres"], profile["moods"], strategy=method, limit=len(books))
            for availability in ("usable_description", "no_usable_description"):
                matches = [b for b in ranked if
                    (int(b.get("description_word_count", 0) or 0) >= 50) == (availability == "usable_description")]
                stratified[(profile_name, method, availability)] = matches[:per_group]

    blind_rows = []
    for (profile_name, method, availability), picks in stratified.items():
        for rank, book in enumerate(picks, start=1):
            source_id = book.get("book_id", "")
            token = hashlib.sha256(f"{seed}|{profile_name}|{method}|{availability}|{rank}|{source_id}".encode()).hexdigest()[:12]
            key_rows.append({"rating_id": token, "profile": profile_name, "method": method,
                             "availability": availability, "rank_within_group": rank, "book_id": source_id,
                             "recommendation_score": book.get("recommendation_score", "")})
            blind_rows.append({"rating_id": token, "profile": profile_name,
                               "profile_description": READER_PROFILES[profile_name]["description"],
                               "description_group": availability,
                               "rank_in_group": rank, "title": book.get("title", ""),
                               "author": book.get("author", "") or "Author not listed",
                               "description": book.get("description", ""),
                               "genres": book.get("genres", ""), "mood_tags": book.get("mood_tags", ""),
                               "relevance_rating_1_5": "", "mood_labels_accurate": "",
                               "reviewer_notes": ""})
    random.Random(seed).shuffle(blind_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    blind_path, key_path = output_dir / "human_comparison_ratings.csv", output_dir / "human_comparison_key.csv"
    with blind_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=blind_rows[0].keys()); writer.writeheader(); writer.writerows(blind_rows)
    with key_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=key_rows[0].keys()); writer.writeheader(); writer.writerows(key_rows)
    # Independent mood-label review sample: usable descriptions only, with
    # model labels kept in a separate key to avoid anchoring the reviewers.
    described = [b for b in books if int(b.get("description_word_count", 0) or 0) >= 50]
    mood_sample = random.Random(seed + 1).sample(described, min(25, len(described)))
    mood_sheet, mood_key = output_dir / "human_mood_review.csv", output_dir / "human_mood_review_key.csv"
    mood_rows, mood_key_rows = [], []
    for i, book in enumerate(mood_sample, start=1):
        token = hashlib.sha256(f"{seed + 1}|mood|{book.get('book_id', '')}".encode()).hexdigest()[:12]
        mood_rows.append({"review_id": token, "title": book.get("title", ""),
                          "description": book.get("description", ""), "human_mood_tags": "",
                          "reviewer_notes": ""})
        mood_key_rows.append({"review_id": token, "book_id": book.get("book_id", ""),
                              "model_mood_tags": book.get("mood_tags", "")})
    with mood_sheet.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=mood_rows[0].keys()); writer.writeheader(); writer.writerows(mood_rows)
    with mood_key.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=mood_key_rows[0].keys()); writer.writeheader(); writer.writerows(mood_key_rows)
    description = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": input_path.resolve().relative_to(PROJECT_DIR).as_posix(),
        "dataset_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "sample_seed": seed, "per_profile_method_description_group": per_group,
        "profiles": list(READER_PROFILES), "methods": list(METHODS),
        "usable_description_threshold_words": 50,
        "rating_protocol": "For every row, independently rate overall fit to the stated reader profile from 1 (not a fit) to 5 (excellent fit). Judge mood-label accuracy separately as yes/no/uncertain; use uncertain when evidence is insufficient. Treat missing descriptions as unavailable evidence, not negative evidence. Do not infer the hidden method; rate books on their merits.",
        "rating_rows": len(blind_rows), "blinded_sheet": blind_path.name, "method_key": key_path.name,
        "independent_mood_review": {"rows": len(mood_rows), "sheet": mood_sheet.name,
                                    "key": mood_key.name, "description_threshold_words": 50,
                                    "instruction": "Annotate zero or more moods from hopeful, dark, suspenseful, adventurous, romantic, reflective, mysterious, humorous. Use semicolon-separated labels; leave blank if no mood can be judged. Do not view the key until annotation is complete."},
        "status": "Prepared for human ratings; no human judgments are present yet.",
        "limitations": "Top-ranked items are sampled within each method/profile/description stratum, so this is a top-of-list sample and does not estimate full-catalog relevance. The same title may appear more than once because its presentation and ranking context differ."
    }
    (output_dir / "human_comparison_protocol.json").write_text(json.dumps(description, indent=2), encoding="utf-8")
    return description


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_DIR / "data/processed/books_sample_5000_with_moods.csv")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_DIR / "results/experiments")
    parser.add_argument("--per-group", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261023)
    args = parser.parse_args()
    print(json.dumps(prepare(args.input, args.output_dir, args.per_group, args.seed), indent=2))


if __name__ == "__main__":
    main()
