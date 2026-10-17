"""Draw-count mathematics for Scrabble racks.

A *draw* is a particular set of physical tiles taken from the bag, so a rack
containing two As can be drawn in C(9, 2) = 36 ways from nine As. The more
draws that produce a rack, the likelier that rack is. Dividing a draw count by
the total number of possible racks, C(100, 7), gives its probability.

Blanks are held in the tile distribution under the key ``"?"``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from itertools import combinations
from math import comb

BLANK = "?"
RACK_SIZE = 7

STANDARD_TILES: dict[str, int] = {
    "A": 9, "B": 2, "C": 2, "D": 4, "E": 12, "F": 2, "G": 3, "H": 2,
    "I": 9, "J": 1, "K": 1, "L": 4, "M": 2, "N": 6, "O": 8, "P": 2,
    "Q": 1, "R": 6, "S": 4, "T": 6, "U": 4, "V": 2, "W": 2, "X": 1,
    "Y": 2, "Z": 1, BLANK: 2,
}  # fmt: skip


def validate_tiles(tiles: Mapping[str, int]) -> dict[str, int]:
    """Return a checked copy of a tile distribution, or raise ``ValueError``."""
    checked: dict[str, int] = {}
    for letter, count in tiles.items():
        valid_key = len(letter) == 1 and (letter == BLANK or "A" <= letter <= "Z")
        if not valid_key:
            raise ValueError(f"Invalid tile {letter!r}: use A-Z or '?' for the blank")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(f"Invalid count for tile {letter!r}: {count!r}")
        checked[letter] = count
    return checked


def total_racks(tiles: Mapping[str, int], rack_size: int = RACK_SIZE) -> int:
    """Number of distinct ways to draw ``rack_size`` tiles from the bag."""
    return comb(sum(tiles.values()), rack_size)


def draw_count(
    letters: Iterable[str], tiles: Mapping[str, int], blanks: int = 0
) -> int:
    """Number of draws giving a rack of exactly these letters plus ``blanks`` blanks.

    ``letters`` are the concrete tiles on the rack. The result is the product
    over letters of C(count in bag, count on rack), times C(blanks in bag,
    blanks on rack). It is zero if the bag cannot supply the rack.
    """
    total = comb(tiles.get(BLANK, 0), blanks)
    for letter, needed in Counter(letters).items():
        total *= comb(tiles.get(letter, 0), needed)
    return total


def alphagram_draw_count(
    alphagram: str, tiles: Mapping[str, int], blanks: int = 0
) -> int:
    """Draws giving a rack with exactly ``blanks`` blanks that can spell ``alphagram``.

    With no blanks this is just :func:`draw_count`. With ``k`` blanks, each
    distinct choice of ``k`` letters of the alphagram to be represented by
    blanks leaves a different set of concrete tiles. Those racks are disjoint,
    so their draw counts are summed.
    """
    if blanks == 0:
        return draw_count(alphagram, tiles)
    total = 0
    # The alphagram is sorted, so combinations arrive sorted and a set removes
    # duplicates such as the two As of AAEINRS.
    for blanked in set(combinations(alphagram, blanks)):
        remaining = Counter(alphagram)
        remaining.subtract(blanked)
        total += draw_count(remaining.elements(), tiles, blanks)
    return total
