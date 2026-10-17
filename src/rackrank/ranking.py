"""Building ranked study lists and filtering them.

Ranks are assigned over the *whole* list for a given length and blank mode,
in descending order of draw count (ties broken alphabetically). Filters are
applied afterwards, so a card's rank never depends on which filters are on.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import combinations

from .lexicon import Lexicon
from .probability import (
    BLANK,
    RACK_SIZE,
    alphagram_draw_count,
    draw_count,
)

ALPHAGRAM = "alphagram"
RACK = "rack"


@dataclass(frozen=True)
class Entry:
    """One valid word with its hooks and definition."""

    word: str
    definition: str
    front_hooks: str
    back_hooks: str


@dataclass(frozen=True)
class Card:
    """One study item: a rack, its valid words and its rank."""

    front: str  # sorted letters; rack-style cards end in one '?' per blank
    entries: tuple[Entry, ...]
    draws: int
    rank: int

    @property
    def single(self) -> bool:
        return len(self.entries) == 1

    @property
    def has_front_hook(self) -> bool:
        return any(e.front_hooks for e in self.entries)

    @property
    def has_back_hook(self) -> bool:
        return any(e.back_hooks for e in self.entries)


@dataclass(frozen=True)
class ListSpec:
    """Which list is being built, and how it is named and tagged."""

    lexicon_name: str
    length: int = RACK_SIZE
    blanks: tuple[int, ...] = (0,)  # numbers of blanks the racks may hold
    style: str = ALPHAGRAM

    @property
    def mode_key(self) -> str:
        if self.style == RACK:
            return f"rack{self.blanks[0]}"
        return f"b{self.blanks[0]}" if len(self.blanks) == 1 else "ball"

    @property
    def display_name(self) -> str:
        base = f"{self.lexicon_name} {self.length}s"
        if self.style == RACK:
            return f"{base}, {self.blanks[0]} blank rack"
        if self.blanks == (0,):
            return base
        if len(self.blanks) == 1:
            plural = "" if self.blanks[0] == 1 else "s"
            return f"{base}, {self.blanks[0]} blank{plural}"
        return f"{base}, any number of blanks"

    def slice_tag(self, rank: int, slice_size: int) -> str:
        low = (rank - 1) // slice_size * slice_size + 1
        high = low + slice_size - 1
        return (
            f"{self.lexicon_name.lower()}::{self.length}::{self.mode_key}"
            f"::{low:04d}-{high:04d}"
        )


def parse_blanks(value: str, tiles: Mapping[str, int]) -> tuple[int, ...]:
    """Turn the ``--blanks`` argument into a tuple of blank counts."""
    available = tiles.get(BLANK, 0)
    if value == "any":
        return tuple(range(available + 1))
    count = int(value)
    if not 0 <= count <= available:
        raise ValueError(f"--blanks must be between 0 and {available}, or 'any'")
    return (count,)


def _entry(lexicon: Lexicon, word: str) -> Entry:
    return Entry(
        word=word,
        definition=lexicon.definitions[word],
        front_hooks=lexicon.front_hooks(word),
        back_hooks=lexicon.back_hooks(word),
    )


def _rank(
    scored: Iterable[tuple[str, int, list[str]]], lexicon: Lexicon
) -> list[Card]:
    ordered = sorted(scored, key=lambda item: (-item[1], item[0]))
    return [
        Card(
            front=front,
            entries=tuple(_entry(lexicon, w) for w in words),
            draws=draws,
            rank=position,
        )
        for position, (front, draws, words) in enumerate(ordered, start=1)
    ]


def build_cards(
    lexicon: Lexicon, tiles: Mapping[str, int], spec: ListSpec
) -> list[Card]:
    """Rank every study item for ``spec``, most likely first.

    Racks the bag cannot supply (zero draws) are left out.
    """
    groups = lexicon.alphagrams(spec.length)

    if spec.style == ALPHAGRAM:
        scored = []
        for letters, words in groups.items():
            draws = sum(alphagram_draw_count(letters, tiles, k) for k in spec.blanks)
            if draws:
                scored.append((letters, draws, words))
        return _rank(scored, lexicon)

    if spec.style != RACK or len(spec.blanks) != 1:
        raise ValueError("Rack-style cards need exactly one blank count")
    blanks = spec.blanks[0]
    racks: dict[str, set[str]] = {}
    for letters, words in groups.items():
        for kept in set(combinations(letters, spec.length - blanks)):
            racks.setdefault("".join(kept), set()).update(words)
    scored = []
    for kept, words in racks.items():
        draws = draw_count(kept, tiles, blanks)
        if draws:
            scored.append((kept + BLANK * blanks, draws, sorted(words)))
    return _rank(scored, lexicon)


def parse_rank_range(value: str) -> tuple[int, int]:
    """Parse ``'1-500'`` (or a single rank, ``'7'``) into inclusive bounds."""
    low_text, _, high_text = value.partition("-")
    low = int(low_text)
    high = int(high_text) if high_text else low
    if low < 1 or high < low:
        raise ValueError(f"Invalid rank range {value!r}")
    return low, high


def filter_cards(
    cards: Iterable[Card],
    rank_range: tuple[int, int] | None = None,
    single_only: bool = False,
    front_hook: bool = False,
    back_hook: bool = False,
) -> list[Card]:
    """Select cards, preserving their ranks and order."""
    selected = []
    for card in cards:
        if rank_range and not rank_range[0] <= card.rank <= rank_range[1]:
            continue
        if single_only and not card.single:
            continue
        if front_hook and not card.has_front_hook:
            continue
        if back_hook and not card.has_back_hook:
            continue
        selected.append(card)
    return selected
