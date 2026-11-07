# BookNooks

BookNooks builds a diverse book catalog from Open Library records, stores source and processed data, and provides notebooks and recommendation interfaces for exploration.

## Repository layout

- `src/data/collect_books.py` collects a fresh sample and quality summary.
- `src/inference/view_books.py` builds a searchable HTML view from the newest processed sample.
- `notebooks/workspace.ipynb` contains the current analysis workflow.
- `data/raw/` stores timestamped API responses; `data/processed/` stores curated CSVs and summaries.
- `results/figures/` stores generated visual and HTML artifacts.
- `research_log/research_log.md` records research decisions and follow-up work.

## Setup and use

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m src.data.collect_books
python3 src/inference/view_books.py
python3 -m src.recommendation.terminal
```

The 100-book API collector is retained for small experiments. To create a fresh 5,000-book catalog quickly, download the monthly Open Library works dump and run the streaming importer:

```bash
mkdir -p data/raw
curl -L --fail -o data/raw/ol_dump_works_latest.txt.gz https://openlibrary.org/data/ol_dump_works_latest.txt.gz
python3 -m src.data.openlibrary_dump
```

The importer reads works in source order and stops once it has 5,000 records with a title and a unique Open Library work ID. It does no category classification, random sampling, or authors-dump scan. It retains subject genres, author IDs, source URLs, and rights notes; author names are blank because resolving them would require a separate pass over the very large authors dump. The default output is `data/processed/books_sample_5000_fast_with_moods.csv`, with a JSON report beside it. Existing files are never replaced unless `--overwrite` is passed. Set a different target or path with `--target` and `--output`.

The active recommender catalog is `data/processed/books_sample_5000_with_moods.csv`. It currently contains 5,000 rows with 5,000 unique work IDs. `results/metrics/data_quality.json` records the latest quality counts. The raw monthly dump is ignored by Git because it is multi-gigabyte.

Open Library recommends its monthly dumps for bulk imports; its public API is intended for low-volume use. The dump and API collection guidance is documented at [Open Library bulk data](https://openlibrary.org/data) and [data dumps](https://openlibrary.org/developers/dumps). The 100-book API collector remains available for a small fresh sample. The HTML viewer reads the newest `books_sample_*.csv` in `data/processed/` and writes `results/figures/books_table.html`.

## Terminal recommender

Run `python3 -m src.recommendation.terminal` from the repository root. It asks you to choose one of four reader profiles or custom preferences, then accepts optional genre, mood, and keyword input. It recommends five books from `data/processed/books_sample_5000_with_moods.csv` and prints the Open Library source for each result. The initial ranking is the genre-only baseline. `--strategy tfidf` and `--strategy mood` are experimental alternatives; no improvement is claimed until they are compared with reader judgments.

## Chat-style UI

Install requirements, then run `streamlit run src/recommendation/chat_app.py` from the repository root. The guided intake asks three questions: preferred genres, current mood, and favorite author. By default, recommendations search the full 5,000-book catalog. A sidebar option can restrict results to the 42 works whose Open Library subjects explicitly include “Translations into English”; untagged translations may be excluded. When recognized genres are provided, books with matching genre subjects are prioritized over text-only similarity. Changing the profile, ranking method, or catalog scope reranks the current recommendations. Covers use Open Library first, then a cached Google Books lookup for a close English-language title/author match; unmatched records show a local placeholder. Set `GOOGLE_BOOKS_API_KEY` to enable the Google Books fallback. Recommendations include Open Library source links. The guided preference blend uses the answers as text, genre, and heuristic mood clues. Genre-only, TF-IDF, and mood-weighted methods remain available for comparison. The app does not use a generative AI chatbot.

The expanded catalog target is 5,000 records. Recompute saved-record and data-quality counts with `python3 -m src.evaluation.data_quality`. Use the 100-record API collector only for small pilot runs; do not use it to bulk harvest individual records.

## Mood label review and experiment protocol

Mood tags are heuristic labels derived during exploration. Create a 25-book human review sheet with `python -m src.evaluation.mood_validation`; reviewers should assign zero or more labels from `hopeful`, `dark`, `suspenseful`, `adventurous`, `romantic`, `reflective`, `mysterious`, `humorous`, and `undetermined`, separated by semicolons. Evaluate completed annotations with `python -m src.evaluation.mood_validation --evaluate results/experiments/mood_review_template.csv`. The blank review sheet is not validation evidence.

Prepare the paired human-rating packet with `python3 -m src.evaluation.prepare_human_comparison`. It covers all four fixed profiles and all four ranking methods (`genre`, `tfidf`, `mood`, and `guided`), with separate samples for usable descriptions (at least 50 words) and records without them. The generated rating sheet is blank by design; the method key should remain hidden from raters until they finish. See `results/experiments/README.md` for rating instructions, subject-label normalization details, and limitations. Do not claim relevance improvement until independent human judgments are collected and analyzed. Record the catalog version, settings, completed ratings, and interpretation in `research_log/research_log.md` and `results/experiments/`.

## Data notes

Raw API responses are retained separately from processed records. Confirm applicable source terms and excerpt permissions before redistributing descriptions or other collected text. Do not commit credentials or local environment files.
