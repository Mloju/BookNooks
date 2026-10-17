"""Create a blinded human-review sheet and score completed mood annotations."""

import argparse
import csv
import json
import random
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
MOODS = {"hopeful", "dark", "suspenseful", "adventurous", "romantic",
         "reflective", "mysterious", "humorous", "undetermined"}


def make_template(source: Path, output: Path, sample_size: int = 25, seed: int = 42) -> None:
    with source.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    sample = random.Random(seed).sample(rows, min(sample_size, len(rows)))
    columns = ["book_id", "title", "description", "model_mood_tags", "human_mood_tags", "reviewer_notes"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for row in sample:
            writer.writerow({
                "book_id": row.get("book_id", ""),
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "model_mood_tags": row.get("mood_tags", ""),
                "human_mood_tags": "",
                "reviewer_notes": "",
            })


def evaluate(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = [row for row in csv.DictReader(file) if row.get("human_mood_tags", "").strip()]
    if not rows:
        return {"reviewed_books": 0, "status": "pending human annotations", "metrics": None}
    exact = 0
    true_pos = false_pos = false_neg = 0
    for row in rows:
        predicted = {x.strip().casefold() for x in row.get("model_mood_tags", "").split(";") if x.strip()}
        human = {x.strip().casefold() for x in row["human_mood_tags"].split(";") if x.strip()}
        unknown = human - MOODS
        if unknown:
            raise ValueError(f"Unrecognized human labels: {sorted(unknown)}")
        exact += predicted == human
        true_pos += len(predicted & human)
        false_pos += len(predicted - human)
        false_neg += len(human - predicted)
    precision = true_pos / (true_pos + false_pos) if true_pos + false_pos else 0.0
    recall = true_pos / (true_pos + false_neg) if true_pos + false_neg else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"reviewed_books": len(rows), "status": "human review recorded", "metrics": {
        "exact_set_match": round(exact / len(rows), 4),
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
    }}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=PROJECT_DIR / "data/processed/books_sample_5000_with_moods.csv")
    parser.add_argument("--template", type=Path, default=PROJECT_DIR / "results/experiments/mood_review_template.csv")
    parser.add_argument("--evaluate", type=Path)
    args = parser.parse_args()
    if args.evaluate:
        print(json.dumps(evaluate(args.evaluate), indent=2))
    else:
        make_template(args.source, args.template)
        print(f"Created review template: {args.template}")
        print("Human labels are blank by design. Fill them with semicolon-separated tags, then run with --evaluate.")


if __name__ == "__main__":
    main()
