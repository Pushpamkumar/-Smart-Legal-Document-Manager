from difflib import SequenceMatcher

from app.schemas.document_schema import DiffEntry, DiffResponse


def build_diff(document_id: int, version_1: int, content_1: str, version_2: int, content_2: str) -> DiffResponse:
    lines_1 = content_1.splitlines()
    lines_2 = content_2.splitlines()
    matcher = SequenceMatcher(None, lines_1, lines_2)

    added: list[str] = []
    removed: list[str] = []
    modified: list[DiffEntry] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added.extend(lines_2[j1:j2])
        elif tag == "delete":
            removed.extend(lines_1[i1:i2])
        elif tag == "replace":
            left = lines_1[i1:i2]
            right = lines_2[j1:j2]
            shared_length = min(len(left), len(right))

            for index in range(shared_length):
                modified.append(DiffEntry(before=left[index], after=right[index]))

            if len(left) > shared_length:
                removed.extend(left[shared_length:])
            if len(right) > shared_length:
                added.extend(right[shared_length:])

    return DiffResponse(
        document_id=document_id,
        version_1=version_1,
        version_2=version_2,
        added=added,
        removed=removed,
        modified=modified,
    )
