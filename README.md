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

Install requirements, then run `streamlit run src/recommendation/chat_app.py` from the repository root. Choose a reader profile and ranking method in the sidebar, describe what you want to read, and review five recommendations with source links. The app is a local demo of the recommender; it does not use a generative AI chatbot.

The expanded catalog target is 5,000 records. Recompute saved-record and data-quality counts with `python3 -m src.evaluation.data_quality`. Use the 100-record API collector only for small pilot runs; do not use it to bulk harvest individual records.

## Mood label review and experiment protocol

Mood tags are heuristic labels derived during exploration. Create a 25-book human review sheet with `python -m src.evaluation.mood_validation`; reviewers should assign zero or more labels from `hopeful`, `dark`, `suspenseful`, `adventurous`, `romantic`, `reflective`, `mysterious`, `humorous`, and `undetermined`, separated by semicolons. Evaluate completed annotations with `python -m src.evaluation.mood_validation --evaluate results/experiments/mood_review_template.csv`. The blank review sheet is not validation evidence.

Compare genre-only, TF-IDF, and mood-weighted rankings on the same user relevance judgments before claiming an improvement. Record the catalog version, split or review set, strategy settings, and metrics in `research_log/research_log.md` and `results/experiments/`. Keep source URLs and rights notes alongside processed records.

## Data notes

Raw API responses are retained separately from processed records. Confirm applicable source terms and excerpt permissions before redistributing descriptions or other collected text. Do not commit credentials or local environment files.
