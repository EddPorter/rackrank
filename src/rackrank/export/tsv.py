"""Tab-separated files for Anki's text import.

Basic and cloze notes need different note types, so they go in separate files.
The first field is always the alphagram: Anki treats it as the note's identity,
so re-importing a file updates existing notes rather than duplicating them.
"""

from __future__ import annotations

from pathlib import Path

from ..ranking import Card, ListSpec
from .common import (
    CLOZE_THRESHOLD,
    basic_fields,
    basic_note_type,
    cloze_fields,
    cloze_note_type,
    is_cloze,
)

_TAGS_COLUMN = 6  # after the five note fields


def _clean(field: str) -> str:
    return field.replace("\t", " ").replace("\n", " ")


def _write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    lines = header + ["\t".join(_clean(f) for f in row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tsv(
    cards: list[Card],
    spec: ListSpec,
    stem: Path,
    slice_size: int,
    cloze_threshold: int = CLOZE_THRESHOLD,
) -> list[Path]:
    """Write ``<stem>-basic.txt`` and ``<stem>-cloze.txt``; skip empty ones."""
    basic_rows, cloze_rows = [], []
    for card in cards:
        tag = spec.slice_tag(card.rank, slice_size)
        if is_cloze(card, cloze_threshold):
            cloze_rows.append([*cloze_fields(card), tag])
        else:
            basic_rows.append([*basic_fields(card), tag])

    written = []
    for suffix, note_type, rows in (
        ("basic", basic_note_type(spec), basic_rows),
        ("cloze", cloze_note_type(spec), cloze_rows),
    ):
        if not rows:
            continue
        path = stem.with_name(f"{stem.name}-{suffix}.txt")
        header = [
            "#separator:tab",
            "#html:true",
            f"#notetype:{note_type}",
            f"#deck:{spec.display_name}",
            f"#tags column:{_TAGS_COLUMN}",
        ]
        _write(path, header, rows)
        written.append(path)
    return written
