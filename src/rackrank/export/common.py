"""Rendering shared by the TSV and .apkg exporters."""

from __future__ import annotations

from html import escape

from ..ranking import Card, Entry, ListSpec

CLOZE_THRESHOLD = 4  # more anagrams than this get a cloze note

BASIC_FIELDS = ["Alphagram", "Count", "Anagrams", "Rank", "Draws"]
CLOZE_FIELDS = ["Alphagram", "Count", "Text", "Rank", "Draws"]


def basic_note_type(spec: ListSpec) -> str:
    return f"{spec.display_name} (Basic)"


def cloze_note_type(spec: ListSpec) -> str:
    return f"{spec.display_name} (Cloze)"


def render_entry(entry: Entry) -> str:
    """HTML for one anagram: front hooks, the word, back hooks, definition."""
    parts = []
    if entry.front_hooks:
        parts.append(f'<span class="hook">{entry.front_hooks}-</span>')
    parts.append(f'<span class="word">{escape(entry.word)}</span>')
    if entry.back_hooks:
        parts.append(f'<span class="hook">-{entry.back_hooks}</span>')
    if entry.definition:
        parts.append(f'<span class="definition">{escape(entry.definition)}</span>')
    return " ".join(parts)


def is_cloze(card: Card, threshold: int = CLOZE_THRESHOLD) -> bool:
    return len(card.entries) > threshold


def basic_fields(card: Card) -> list[str]:
    anagrams = "<br>".join(render_entry(e) for e in card.entries)
    return [
        card.front,
        str(len(card.entries)),
        anagrams,
        str(card.rank),
        f"{card.draws:,}",
    ]


def cloze_fields(card: Card) -> list[str]:
    """Cloze note fields: one deletion per anagram, so one card per anagram."""
    lines = []
    for number, entry in enumerate(card.entries, start=1):
        lines.append("{{c%d::%s}}" % (number, render_entry(entry)))
    return [
        card.front,
        str(len(card.entries)),
        "<br>".join(lines),
        str(card.rank),
        f"{card.draws:,}",
    ]

