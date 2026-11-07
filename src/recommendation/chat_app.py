"""Step-by-step Streamlit intake for the BookNooks guided recommender."""

from __future__ import annotations

import csv
import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote_plus

import requests
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.recommendation.engine import READER_PROFILES, recommend  # noqa: E402

CATALOG_PATH = PROJECT_DIR / "data" / "processed" / "books_sample_5000_with_moods.csv"
PLACEHOLDER_COVER_PATH = PROJECT_DIR / "src" / "recommendation" / "book_cover_placeholder.svg"
QUESTIONS = [
    ("genres", "What genres do you like?"),
    ("mood", "What’s on your mind lately? Use one word if you like, such as sad, love, or quiet."),
    ("author", "Who is your favorite author, if any?"),
]
MOOD_ALIASES = {
    "sad": "reflective", "sadness": "reflective", "grief": "reflective",
    "quiet": "reflective", "quite": "reflective", "calm": "reflective", "peaceful": "reflective",
    "love": "romantic", "loveful": "romantic", "romance": "romantic",
    "happy": "hopeful", "hope": "hopeful", "hopeful": "hopeful",
    "scared": "suspenseful", "anxious": "suspenseful", "tense": "suspenseful",
    "curious": "mysterious", "dark": "dark", "funny": "humorous",
    "adventurous": "adventurous",
}
MOOD_TERMS = (
    "hopeful", "dark", "suspenseful", "adventurous", "romantic",
    "reflective", "mysterious", "humorous",
)
GENRE_TERMS = (
    "fantasy", "adventure", "magic", "mystery", "romance", "horror",
    "science fiction", "mythology", "fairy tales", "epic", "dark fantasy",
    "historical fiction", "biography", "memoir", "nonfiction", "science",
    "philosophy", "poetry", "drama", "children", "young adult", "western",
    "crime", "detective", "thriller", "survival", "history",
)
TRANSLATION_SUBJECT = "translations into english"


@st.cache_data
def load_catalog(path: str) -> list[dict]:
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def phrases_in(text: str, phrases: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    return [phrase for phrase in phrases
            if re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", lowered)]


def english_translations(books: list[dict]) -> list[dict]:
    """Require explicit Open Library subject evidence of an English translation."""
    return [book for book in books
            if TRANSLATION_SUBJECT in (book.get("genres", "") or "").casefold()]


def _normalized(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (value or "").casefold()))


def _author_match(catalog_author: str, result_authors: list[str]) -> bool:
    expected = {_normalized(name) for name in (catalog_author or "").split(";") if name.strip()}
    expected.discard("")
    actual = {_normalized(name) for name in result_authors}
    return bool(expected & actual)


@st.cache_data(ttl=7 * 24 * 60 * 60, max_entries=2000, show_spinner=False)
def cover_url(book_id: str, title: str, author: str, google_api_key: str = "") -> str:
    """Prefer an Open Library work cover, then use a confidently matched English Google Books volume."""
    work_id = (book_id or "").rsplit("/", 1)[-1]
    open_library_url = f"https://covers.openlibrary.org/b/olid/{work_id}-M.jpg?default=false" if work_id else ""
    if open_library_url:
        try:
            response = requests.get(open_library_url, timeout=5, stream=True)
            response.close()
            if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                return open_library_url
        except requests.RequestException:
            pass

    if not title.strip():
        return ""
    query = f'intitle:"{title}"'
    if author.strip():
        query += f' inauthor:"{author.split(";")[0].strip()}"'
    params = {"q": query, "langRestrict": "en", "printType": "books", "maxResults": 5}
    if not google_api_key:
        return ""
    params["key"] = google_api_key
    try:
        response = requests.get("https://www.googleapis.com/books/v1/volumes", params=params, timeout=8)
        response.raise_for_status()
        items = response.json().get("items", [])
    except (requests.RequestException, ValueError):
        return ""

    expected_title = _normalized(title)
    for item in items:
        volume = item.get("volumeInfo", {})
        if volume.get("language", "").casefold() != "en":
            continue
        found_title = _normalized(volume.get("title", ""))
        title_match = SequenceMatcher(None, expected_title, found_title).ratio()
        author_match = _author_match(author, volume.get("authors", []))
        # Require a strong title match, or both a substantial title overlap and matching author.
        if title_match < 0.84 and not (author_match and title_match >= 0.62):
            continue
        image_links = volume.get("imageLinks", {})
        image = image_links.get("thumbnail") or image_links.get("smallThumbnail")
        if image:
            return image.replace("http://", "https://", 1)
    return ""


def initialize_session() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("question_index", 0)
    st.session_state.setdefault("preferences", {})


def make_recommendations(books: list[dict], preferences: dict, profile_key: str,
                         strategy: str) -> tuple[list[dict], str]:
    profile = READER_PROFILES.get(profile_key, {})
    profile_genres = profile.get("genres", "")
    profile_moods = profile.get("moods", "")
    genre_answer = preferences.get("genres", "")
    mood_answer = preferences.get("mood", "").strip().casefold()

    detected_genres = phrases_in(genre_answer, GENRE_TERMS)
    # Prefer recognized genre concepts over conversational filler ("I like",
    # "books about", etc.), which otherwise dilutes exact genre matching.
    user_genres = detected_genres or genre_answer
    genres = "; ".join(dict.fromkeys(part for part in (profile_genres, user_genres) if part)).strip("; ")

    detected_moods = phrases_in(mood_answer, MOOD_TERMS)
    detected_moods.extend(MOOD_ALIASES[word] for word in re.findall(r"[a-z]+", mood_answer)
                          if word in MOOD_ALIASES)
    moods = "; ".join(dict.fromkeys([profile_moods, *detected_moods])).strip("; ")
    query = " ".join(preferences.get(key, "") for key in
                      ("author", "mood")
                      if preferences.get(key, "").strip())

    ranked = recommend(books, genres=genres, moods=moods, query=query,
                       strategy=strategy, limit=len(books))
    # An experimental text score must not push books with no requested-genre
    # evidence above actual genre matches when such matches exist.
    matched = [book for book in ranked if book.get("genre_match", 0) > 0]
    if matched:
        ranked = matched
    picks = ranked[:5]
    return picks, genres


def main() -> None:
    st.set_page_config(page_title="BookNooks recommender", page_icon="📚", layout="centered")
    st.title("📚 BookNooks")
    st.caption("A guided recommender that uses your reading preferences to rank catalog matches.")

    with st.sidebar:
        st.header("Recommendation settings")
        profile_options = ["Custom preferences", *[name.title() for name in READER_PROFILES]]
        selected_label = st.selectbox("Reader profile", profile_options)
        strategy_label = st.selectbox(
            "Ranking method",
            ["Guided preference blend", "Genre-only baseline", "TF-IDF experiment", "Mood-weighted experiment"],
        )
        strategy = {
            "Guided preference blend": "guided",
            "Genre-only baseline": "genre",
            "TF-IDF experiment": "tfidf",
            "Mood-weighted experiment": "mood",
        }[strategy_label]
        translations_only = st.checkbox(
            "Limit to works tagged as English translations", value=False,
            help="Only 42 catalog records currently carry this explicit subject tag. Untagged translations may be excluded.",
        )
        st.caption("The guided blend uses your book and author answers as text clues and mood tags as heuristic signals. Experimental methods have not been shown to improve relevance.")
        if st.button("Start over", use_container_width=True):
            for key in ("messages", "question_index", "preferences"):
                st.session_state.pop(key, None)
            st.rerun()

    if not CATALOG_PATH.exists():
        st.error(f"Catalog not found: {CATALOG_PATH}")
        st.stop()
    catalog = load_catalog(str(CATALOG_PATH))
    books = english_translations(catalog) if translations_only else catalog
    if translations_only:
        st.caption(f"Showing {len(books)} works explicitly tagged as translations into English · covers and source links where available")
        st.caption("The Open Library work title can remain in its original language; this catalog does not include English-edition titles for every work.")
    else:
        st.caption(f"Searching all {len(books):,} catalog works · covers and source links where available")
    if not books:
        st.warning("This catalog has no records explicitly marked as translations into English, so there are no recommendations to show.")
        st.stop()

    initialize_session()
    current_settings = (selected_label, strategy, translations_only)
    previous_settings = st.session_state.get("recommendation_settings")
    if (previous_settings and previous_settings != current_settings
            and st.session_state.question_index >= len(QUESTIONS)
            and st.session_state.preferences):
        profile_key = selected_label.casefold()
        picks, genres = make_recommendations(books, st.session_state.preferences,
                                              profile_key, strategy)
        for message in reversed(st.session_state.messages):
            if message.get("books") is not None:
                message["books"] = picks
                if picks:
                    message["content"] = (
                        f"I reranked the catalog using **{strategy_label.lower()}** for your genre preferences "
                        f"(`{genres}`). Here are five books to consider. Mood tags are heuristic."
                    )
                else:
                    message["content"] = "I couldn’t find recommendations in this catalog subset. Try broader preferences or turn off the translation-only filter."
                break
    st.session_state.recommendation_settings = current_settings
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for book in message.get("books", []):
                with st.container(border=True):
                    left, right = st.columns([1, 3])
                    image_url = cover_url(
                        book.get("book_id", ""), book.get("title", ""), book.get("author", ""),
                        os.getenv("GOOGLE_BOOKS_API_KEY", ""),
                    )
                    if image_url:
                        left.image(image_url, width=120)
                    else:
                        left.image(str(PLACEHOLDER_COVER_PATH), width=120)
                    right.markdown(f"**{book.get('title') or 'Untitled'}**")
                    right.write(book.get("author") or "Author not listed")
                    genres = book.get("matched_genres") or []
                    right.caption("Matched genres: " + (", ".join(genres[:4]) if genres else "catalog match"))
                    moods = book.get("mood_tags", "")
                    known_moods = [mood.strip() for mood in moods.split(";")
                                   if mood.strip().casefold() not in {"unknown", "undetermined"}]
                    if known_moods:
                        right.caption(f"Mood tags (heuristic): {'; '.join(known_moods)}")
                    source_url = book.get("source_url")
                    if source_url:
                        right.markdown(f"[Open Library source]({source_url})")

    question_index = st.session_state.question_index
    if question_index < len(QUESTIONS):
        key, question = QUESTIONS[question_index]
        with st.chat_message("assistant"):
            st.markdown(f"**{question_index + 1} of {len(QUESTIONS)}**  {question}")
        with st.form(key=f"intake_{question_index}", clear_on_submit=True):
            answer = st.text_input("Your answer (optional)", key=f"answer_{question_index}",
                                   placeholder="Type an answer or skip")
            next_step = st.form_submit_button("Continue")
        if next_step:
            shown_answer = answer.strip() or "Skipped"
            st.session_state.messages.extend([
                {"role": "assistant", "content": f"**{question_index + 1} of {len(QUESTIONS)}**  {question}"},
                {"role": "user", "content": shown_answer},
            ])
            st.session_state.preferences[key] = answer.strip()
            st.session_state.question_index += 1
            if st.session_state.question_index == len(QUESTIONS):
                profile_key = selected_label.casefold()
                picks, genres = make_recommendations(books, st.session_state.preferences,
                                                      profile_key, strategy)
                if picks:
                    response = (f"I used **{strategy_label.lower()}** with your genre preferences (`{genres}`) "
                                f"and searched {len(books):,} books in the selected catalog scope. "
                                "Here are five books to consider. Mood tags are heuristic.")
                    st.session_state.messages.append({"role": "assistant", "content": response, "books": picks})
                else:
                    st.session_state.messages.append({"role": "assistant", "content":
                        "I couldn’t find a match for those preferences among the catalog records explicitly marked as English translations. Try a broader genre or a different ranking method."})
            st.rerun()


if __name__ == "__main__":
    main()
