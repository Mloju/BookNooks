"""Heuristic mood labels; these require human validation before evaluation claims."""

import re

MOOD_KEYWORDS = {
    "hopeful": ("hope", "hopeful", "optimistic", "triumph", "courage", "inspiring", "overcome", "dream"),
    "dark": ("dark", "grim", "brutal", "bleak", "cruel", "death", "despair", "horror", "evil"),
    "suspenseful": ("suspense", "danger", "threat", "mystery", "chase", "secret", "murder", "betrayal"),
    "humorous": ("funny", "humor", "humour", "comedy", "comic", "hilarious", "witty"),
    "romantic": ("romance", "romantic", "love", "passion", "beloved", "relationship"),
    "reflective": ("reflect", "memory", "regret", "grief", "loss", "identity", "meaning", "loneliness"),
    "adventurous": ("adventure", "journey", "quest", "explore", "battle", "warrior", "expedition", "travel"),
    "mysterious": ("mysterious", "enigma", "puzzle", "unknown", "uncover", "investigate"),
}


def tag_mood(description: str) -> str:
    """Apply the notebook's existing keyword rules to a description."""
    if not description or not description.strip():
        return "unknown"
    text = description.casefold()
    found = []
    for mood, keywords in MOOD_KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(word), text) for word in keywords):
            found.append(mood)
    return "; ".join(found) if found else "undetermined"
