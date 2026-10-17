"""Collect a timestamped fantasy sample from Open Library."""

from datetime import datetime, timezone
from pathlib import Path

from src.data.openlibrary import collect_records, fetch_search_results, write_collection

PROJECT_DIR = Path(__file__).resolve().parents[2]


def main() -> None:
    query = "subject:fantasy"
    target = 100
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_dir = PROJECT_DIR / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_search = raw_dir / f"search_{timestamp}.json"
    raw_details = raw_dir / f"work_details_{timestamp}"
    processed = PROJECT_DIR / "data" / "processed"

    print(f"Collecting up to {target} books for {query} ...")
    try:
        search_data = fetch_search_results(query=query, limit=target)
    except Exception as error:
        raise SystemExit(f"Could not retrieve Open Library results: {error}") from error

    books = collect_records(search_data, raw_details_dir=raw_details)
    csv_path, summary_path, report = write_collection(
        books, search_data, raw_search, raw_details, processed, target, query
    )
    print("\nCOLLECTION REPORT")
    print(f"Targeted: {target}")
    print(f"Search results returned: {report['search_results_returned']}")
    print(f"Records saved: {report['saved_records']} ({report['unique_saved_book_ids']} unique)")
    print(f"Usable descriptions (50+ words): {report['usable_descriptions']}/{report['saved_records']}")
    print(f"Records with genres: {report['records_with_genres']}/{report['saved_records']}")
    print(f"Source and rights fields recorded: {report['source_url_records']}/{report['saved_records']}")
    print(f"Processed CSV: {csv_path}")
    print(f"Quality report: {summary_path}")


if __name__ == "__main__":
    main()
