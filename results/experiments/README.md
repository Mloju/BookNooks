# Human evaluation packet

## Current status

The 5,000-row audit found 731 records (14.62%) with descriptions of at least 50 words. The paired profile ratings in `profile_recommendation_ratings.csv` are AI-assisted metadata-fit proxies, not human judgments. They must not be cited as evidence that any method improves reader relevance.

`human_comparison_ratings.csv` is the blinded rating sheet. It contains 96 rows: four fixed profiles × four ranking methods × two description strata × three recommendations. The methods are `genre`, `tfidf`, `mood`, and `guided`. `human_comparison_key.csv` maps randomized rating IDs back to methods and original catalog IDs; keep this file away from raters until their ratings are complete. `human_comparison_protocol.json` records the catalog hash, seed, cutoff, and procedure.

`human_mood_review.csv` is a separate blind sheet of up to 25 randomly selected descriptions of at least 50 words. Reviewers enter zero or more mood labels from `hopeful`, `dark`, `suspenseful`, `adventurous`, `romantic`, `reflective`, `mysterious`, and `humorous` (semicolon-separated). `human_mood_review_key.csv` holds model labels and IDs; keep it hidden until annotation is complete. This makes it possible to assess mood-tag quality without exposing the model label first.

## Procedure

1. Have at least two people independently rate the blinded sheet. Use the profile description shown on each row and rate fit from 1 (not a fit) to 5 (excellent fit). Rate mood-label accuracy as `yes`, `no`, or `uncertain`; use `uncertain` when the available text cannot support a judgment. Leave mood accuracy blank when there is no usable description.
2. Keep all ratings independent. Do not share the method key or discuss individual rows before both raters finish. Preserve separate copies or columns for each rater; do not overwrite one person's judgment with another's.
3. Reconnect IDs with the key only after rating. Report method results by profile and description stratum. Include number of ratings and inter-rater agreement; treat small differences as exploratory. This top-three-per-stratum sample measures only the top of each ranked list and cannot establish catalog-wide relevance.
4. Review mood labels independently on a separate random sample of descriptions >=50 words. The existing `mood_review_template.csv` contains a prior AI-assisted pass; it is not the new human sample. Record human reviewers and date in the research log, and keep the AI annotations distinguishable from human annotations.
5. Do not claim improvement until independent human ratings are entered and analyzed. The four methods use fixed settings in `src/recommendation/engine.py`; the guided method uses the fixed profile's genre and mood text as the guided inputs in this controlled comparison (it does not simulate a live user's custom answers).

## Subject-label normalization

The source's 9,609 distinct subject strings are retained verbatim in the `genres` field as semicolon-separated labels. The audit trims whitespace around each label when counting distinct values, but does not merge synonyms, translate labels, resolve hierarchy, or deduplicate semantically equivalent subjects. At recommendation time, `tokens()` case-folds text and extracts lowercase ASCII alphanumeric tokens; punctuation becomes separators. Genre matching is exact token intersection against profile terms, divided by the number of requested profile tokens. Thus `Mystery and crime` matches `mystery` and `crime`, but there is no ontology or synonym mapping, phrase weighting, stemming, or language normalization. TF-IDF uses the stored genre text as-is (plus title, author, and description). This is a known source of noisy genre matching; any future canonical mapping should be versioned and evaluated as a separate method setting.

## Reproduce the rating packet

From the repository root, run:

```bash
python3 -m src.evaluation.prepare_human_comparison
```

The default sample is deterministic (seed `20261023`), uses the active 5,000-book CSV, selects three top-ranked items in each profile/method/description group, and writes the three packet files above. No human ratings are supplied by this command.
