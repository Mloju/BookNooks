# Research log

## Project notes

- Dataset: fantasy book metadata and descriptions collected from Open Library.
- Collection script: `src/data/collect_books.py`.
- Current exploratory analysis: `notebooks/workspace.ipynb`.
- Keep collection runs timestamped so source snapshots and derived data remain traceable.
- The active 5,000-book catalog at `data/processed/books_sample_5000_with_moods.csv` contains 5,000 rows and 5,000 unique Open Library work IDs. Recomputed quality counts: 731 descriptions meet the 50-word threshold (14.62%); all 5,000 have genre subjects, a source URL, a rights note, and a heuristic mood tag. The original 100-book catalog remains available separately.
- The earlier catalog expansion used a category-balanced dump scan. Per the project decision to prioritize speed without category balancing, future imports use `src/data/openlibrary_dump.py`: stream works in source order, accept non-empty titles with unique work IDs, and stop at the target. It writes to `books_sample_5000_fast_with_moods.csv` so it cannot replace the active catalog by default. No full-dump scan is currently running.
- The active catalog retains its Open Library source URL and rights note per row. The fast importer retains those fields, subject genres, and author IDs. It does not resolve author names because that requires scanning the separate large authors dump.
- Terminal recommendations use genre-only ranking as the baseline. TF-IDF and mood-weighted rankings are experimental and have not been shown to improve relevance.
- Mood labels are heuristic. A 25-book human review template is generated at `results/experiments/mood_review_template.csv`; human annotations and validation metrics are pending.
- Recommendation rows retain Open Library source URLs and rights notes from the underlying processed data.

## Open questions

- Complete and evaluate the human mood review before treating mood tags as validated.
- Collect reader relevance judgments and compare all strategies on the same books and queries before reporting a winning recommender.
- Append experiment settings and results here when evaluation is completed.
