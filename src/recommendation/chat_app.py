"""Small Streamlit chat interface for trying BookNooks recommendations."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.recommendation.engine import READER_PROFILES, recommend  # noqa: E402

CATALOG_PATH = PROJECT_DIR / "data" / "processed" / "books_sample_5000_with_moods.csv"
MOOD_TERMS = (
    "hopeful", "dark", "suspenseful", "adventurous", "romantic",
    "reflective", "mysterious", "humorous",
)
GENRE_TERMS = (
    "fantasy", "adventure", "magic", "mystery", "romance", "horror",
    "science fiction", "mythology", "fairy tales", "epic", "dark fantasy",
    "historical fiction", "biography", "memoir", "nonfiction", "science",
    "philosophy", "poetry", "drama", "children", "young adult", "western",
    "crime", "detective",
)


@st.cache_data
def load_catalog(path: str) -> list[dict]:
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def phrases_in(text: str, phrases: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    return [phrase for phrase in phrases
            if re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", lowered)]


def main() -> None:
    st.set_page_config(page_title="BookNooks recommender", page_icon="📚", layout="centered")
    st.title("📚 BookNooks")
    st.caption("A chat-style demo for exploring book recommendations from the current catalog.")

    with st.sidebar:
        st.header("Recommendation settings")
        profile_options = ["Custom preferences", *[name.title() for name in READER_PROFILES]]
        selected_label = st.selectbox("Reader profile", profile_options)
        strategy_label = st.selectbox(
            "Ranking method",
            ["Genre-only baseline", "TF-IDF experiment", "Mood-weighted experiment"],
        )
        strategy = {
            "Genre-only baseline": "genre",
            "TF-IDF experiment": "tfidf",
            "Mood-weighted experiment": "mood",
        }[strategy_label]
        st.caption("The genre-only method is the baseline. Experimental methods have not been shown to improve relevance.")
        if st.button("Start a new chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    if not CATALOG_PATH.exists():
        st.error(f"Catalog not found: {CATALOG_PATH}")
        st.stop()
    books = load_catalog(str(CATALOG_PATH))
    st.caption(f"Catalog: {len(books)} books · recommendations include source links")

    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Tell me what kind of book you want to read. Try something like “fantasy adventure with a hopeful mood” or choose a reader profile in the sidebar.",
        }]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for book in message.get("books", []):
                with st.container(border=True):
                    st.markdown(f"**{book.get('title') or 'Untitled'}**")
                    st.write(book.get("author") or "Author not listed")
                    genres = book.get("matched_genres") or []
                    st.caption("Matched genres: " + (", ".join(genres[:4]) if genres else "catalog match"))
                    moods = book.get("mood_tags", "")
                    if moods:
                        st.caption(f"Mood tags: {moods}")
                    source_url = book.get("source_url")
                    if source_url:
                        st.markdown(f"[Open Library source]({source_url})")

    request = st.chat_input("What would you like to read?")
    if request:
        st.session_state.messages.append({"role": "user", "content": request})
        profile_key = selected_label.casefold()
        if profile_key == "custom preferences":
            default_genres, default_moods = "", ""
        else:
            profile = READER_PROFILES[profile_key]
            default_genres, default_moods = profile["genres"], profile["moods"]

        detected_genres = phrases_in(request, GENRE_TERMS)
        detected_moods = phrases_in(request, MOOD_TERMS)
        genres = "; ".join(dict.fromkeys([default_genres, *detected_genres])).strip("; ")
        moods = "; ".join(dict.fromkeys([default_moods, *detected_moods])).strip("; ")
        if not genres:
            # The catalog is a fantasy collection, so this is a useful genre baseline
            # when a free-text request contains no recognized genre phrase.
            genres = "fantasy"

        picks = recommend(
            books, genres=genres, moods=moods, query=request,
            strategy=strategy, limit=5,
        )
        response = (
            f"I used **{strategy_label.lower()}** with genres `{genres}`. "
            "Here are five books to consider."
        )
        st.session_state.messages.append({"role": "assistant", "content": response, "books": picks})
        st.rerun()


if __name__ == "__main__":
    main()
