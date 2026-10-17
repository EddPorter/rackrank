"""Anki package export via genanki (an optional dependency)."""

from __future__ import annotations

import zlib
from pathlib import Path

from ..ranking import Card, ListSpec
from .common import (
    BASIC_FIELDS,
    CLOZE_EACH,
    CLOZE_FIELDS,
    CLOZE_THRESHOLD,
    basic_fields,
    basic_note_type,
    cloze_fields,
    cloze_note_type,
    is_cloze,
)
from .templates import (
    BASIC_AFMT,
    BASIC_QFMT,
    CLOZE_AFMT,
    CLOZE_QFMT,
    CSS,
)


def _stable_id(name: str) -> int:
    """A deterministic 31-bit ID, so repeated exports share model and deck IDs."""
    return zlib.crc32(name.encode("utf-8")) & 0x7FFFFFFF or 1


def write_apkg(
    cards: list[Card],
    spec: ListSpec,
    stem: Path,
    slice_size: int,
    cloze_threshold: int = CLOZE_THRESHOLD,
    cloze_mode: str = CLOZE_EACH,
) -> Path:
    try:
        import genanki
    except ImportError:
        raise SystemExit(
            "The .apkg export needs genanki: pip install 'rackrank[apkg]'"
        ) from None

    def fields(names: list[str]) -> list[dict[str, str]]:
        return [{"name": n} for n in names]

    basic_name, cloze_name = basic_note_type(spec), cloze_note_type(spec)
    basic_model = genanki.Model(
        _stable_id(basic_name),
        basic_name,
        fields=fields(BASIC_FIELDS),
        templates=[{"name": "Card 1", "qfmt": BASIC_QFMT, "afmt": BASIC_AFMT}],
        css=CSS,
    )
    cloze_model = genanki.Model(
        _stable_id(cloze_name),
        cloze_name,
        fields=fields(CLOZE_FIELDS),
        templates=[{"name": "Cloze", "qfmt": CLOZE_QFMT, "afmt": CLOZE_AFMT}],
        css=CSS,
        model_type=genanki.Model.CLOZE,
    )
    deck = genanki.Deck(_stable_id(spec.display_name), spec.display_name)

    for card in cards:
        clozed = is_cloze(card, cloze_threshold)
        # The GUID is derived from the alphagram and note type alone, so
        # re-importing updates a note in place, as the TSV import does.
        deck.add_note(
            genanki.Note(
                model=cloze_model if clozed else basic_model,
                fields=cloze_fields(card, cloze_mode) if clozed else basic_fields(card),
                tags=[spec.slice_tag(card.rank, slice_size)],
                guid=genanki.guid_for(
                    cloze_name if clozed else basic_name, card.front
                ),
            )
        )

    path = stem.with_name(f"{stem.name}.apkg")
    genanki.Package(deck).write_to_file(str(path))
    return path
