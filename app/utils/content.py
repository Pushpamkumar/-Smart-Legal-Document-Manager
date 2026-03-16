import re


def normalize_content(content: str) -> str:
    stripped_lines = [line.strip() for line in content.splitlines()]
    normalized = "\n".join(stripped_lines).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized
