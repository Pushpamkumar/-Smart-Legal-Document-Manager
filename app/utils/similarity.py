from difflib import SequenceMatcher

from app.utils.content import normalize_content


def similarity_score(old_content: str, new_content: str) -> float:
    old_normalized = normalize_content(old_content)
    new_normalized = normalize_content(new_content)
    return SequenceMatcher(None, old_normalized, new_normalized).ratio()
