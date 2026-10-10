
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# -----------------------------------------
# 1. PROJECT SETTINGS
# -----------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://openlibrary.org"
QUERY = "subject:fantasy"
SAMPLE_SIZE = 100

# A description is usable if it contains at least 50 words.
MIN_DESCRIPTION_WORDS = 50

HEADERS = {
    "User-Agent": "BookNookCapstone/1.0"
}

# -----------------------------------------
# 2. START THE COLLECTION
# -----------------------------------------

collection_date = datetime.now(timezone.utc).isoformat()
timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

print("Starting BookNook data collection...")

try:
    response = requests.get(
        f"{BASE_URL}/search.json",
        params={
            "q": QUERY,
            "limit": SAMPLE_SIZE,
            "fields": (
                "key,title,author_name,"
                "first_publish_year,subject"
            ),
        },
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()
    search_data = response.json()

except (requests.RequestException, ValueError) as error:
    print(f"Could not retrieve book search results: {error}")
    raise SystemExit(1)

# Save the original search response unchanged.
raw_search_file = RAW_DIR / f"search_{timestamp}.json"

raw_search_file.write_text(
    json.dumps(search_data, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

# -----------------------------------------
# 3. COLLECT BOOK DETAILS
# -----------------------------------------

books = []

raw_details_dir = RAW_DIR / f"work_details_{timestamp}"
raw_details_dir.mkdir(parents=True, exist_ok=True)

for item in search_data.get("docs", []):
    work_id = item.get("key")

    if not work_id:
        continue

    description = ""
    detail_retrieved = False

    try:
        detail_response = requests.get(
            f"{BASE_URL}{work_id}.json",
            headers=HEADERS,
            timeout=30,
        )

        detail_response.raise_for_status()
        details = detail_response.json()
        detail_retrieved = True

        # Preserve the original work response.
        raw_file = raw_details_dir / (
            f"{work_id.split('/')[-1]}.json"
        )

        raw_file.write_text(
            json.dumps(details, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Open Library descriptions can be text or dictionaries.
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

    book = {
        "book_id": work_id,
        "title": item.get("title") or "",
        "author": "; ".join(item.get("author_name") or []),
        "publication_year": item.get("first_publish_year") or "",
        "description": description.strip(),
        "description_word_count": len(description.split()),
        "genres": "; ".join(subjects),
        "source_url": f"{BASE_URL}{work_id}",
        "rights_notes": (
            "Verify applicable source terms and excerpt permissions "
            "before reuse."
        ),
        "details_retrieved": detail_retrieved,
    }

    books.append(book)

    # Be considerate of the public API.
    time.sleep(1)

# -----------------------------------------
# 4. SAVE THE COLLECTED DATA
# -----------------------------------------

fields = [
    "book_id",
    "title",
    "author",
    "publication_year",
    "description",
    "description_word_count",
    "genres",
    "source_url",
    "rights_notes",
    "details_retrieved",
]

csv_file = PROCESSED_DIR / f"books_sample_{timestamp}.csv"

with csv_file.open(
    "w", newline="", encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(books)

# -----------------------------------------
# 5. CHECK DATA QUALITY
# -----------------------------------------

total = len(books)

usable_descriptions = sum(
    book["description_word_count"] >= MIN_DESCRIPTION_WORDS
    for book in books
)

with_genres = sum(
    bool(book["genres"].strip())
    for book in books
)

# Mood is not provided directly by this source.
# A usable description is a prerequisite for later mood tagging.
mood_derivable = usable_descriptions

with_all_three = sum(
    book["description_word_count"] >= MIN_DESCRIPTION_WORDS
    and bool(book["genres"].strip())
    for book in books
)

def percentage(count, total):
    if total == 0:
        return 0.0
    return round(count / total * 100, 2)


quality_summary = {
    "collection_date_utc": collection_date,
    "source": "Open Library API",
    "query": QUERY,
    "requested_sample_size": SAMPLE_SIZE,
    "total_records_collected": total,
    "description_word_threshold": MIN_DESCRIPTION_WORDS,
    "usable_descriptions": usable_descriptions,
    "usable_descriptions_percent": percentage(
        usable_descriptions, total
    ),
    "records_with_genres": with_genres,
    "records_with_genres_percent": percentage(
        with_genres, total
    ),
    "records_with_mood_derivable": mood_derivable,
    "records_with_mood_derivable_percent": percentage(
        mood_derivable, total
    ),
    "records_with_all_three": with_all_three,
    "records_with_all_three_percent": percentage(
        with_all_three, total
    ),
    "note": (
        "Mood availability means a description meets the word "
        "threshold. Mood tags have not yet been generated or "
        "validated by human review."
    ),
    "raw_search_file": str(raw_search_file.relative_to(PROJECT_DIR)),
    "processed_csv": str(csv_file.relative_to(PROJECT_DIR)),
}

summary_file = PROCESSED_DIR / f"quality_summary_{timestamp}.json"

summary_file.write_text(
    json.dumps(quality_summary, indent=2),
    encoding="utf-8",
)

# -----------------------------------------
# 6. REPORT THE RESULTS
# -----------------------------------------

print("\nDATA COLLECTION COMPLETE")
print("------------------------")
print(f"Source: Open Library API")
print(f"Query: {QUERY}")
print(f"Records collected: {total}")

print(
    f"Usable descriptions: {usable_descriptions}/{total} "
    f"({quality_summary['usable_descriptions_percent']}%)"
)

print(
    f"Records with genres: {with_genres}/{total} "
    f"({quality_summary['records_with_genres_percent']}%)"
)

print(
    f"Mood-derivable descriptions: {mood_derivable}/{total} "
    f"({quality_summary['records_with_mood_derivable_percent']}%)"
)

print(
    f"Records with all three: {with_all_three}/{total} "
    f"({quality_summary['records_with_all_three_percent']}%)"
)

print(f"\nRaw response: {raw_search_file}")
print(f"Processed data: {csv_file}")
print(f"Quality report: {summary_file}")
