"""Dictionary loading, alphagram grouping and hook lookup.

Loaders are registered in :data:`LOADERS` by format name, so a different
lexicon or file layout can be supported by adding one function that returns a
:class:`Lexicon`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from string import ascii_lowercase, ascii_uppercase

_LETTERS = frozenset(ascii_uppercase)


def alphagram(word: str) -> str:
    """The letters of ``word`` sorted alphabetically."""
    return "".join(sorted(word))


@dataclass
class Lexicon:
    """A word list with optional definitions."""

    name: str
    definitions: dict[str, str]
    skipped: int = 0  # lines the loader could not interpret
    _by_alphagram: dict[int, dict[str, list[str]]] = field(
        default_factory=dict, repr=False
    )

    def __contains__(self, word: object) -> bool:
        return word in self.definitions

    def alphagrams(self, length: int) -> dict[str, list[str]]:
        """Map each alphagram of the given length to its sorted valid words."""
        if length not in self._by_alphagram:
            groups: dict[str, list[str]] = defaultdict(list)
            for word in self.definitions:
                if len(word) == length:
                    groups[alphagram(word)].append(word)
            self._by_alphagram[length] = {k: sorted(v) for k, v in groups.items()}
        return self._by_alphagram[length]

    def front_hooks(self, word: str) -> str:
        """Lower-case letters that can be added before ``word`` to make a word."""
        return "".join(
            c for c in ascii_lowercase if c.upper() + word in self.definitions
        )

    def back_hooks(self, word: str) -> str:
        """Lower-case letters that can be added after ``word`` to make a word."""
        return "".join(
            c for c in ascii_lowercase if word + c.upper() in self.definitions
        )


def load_wordlist(path: Path, name: str) -> Lexicon:
    """Read one word per line, optionally followed by whitespace and a definition.

    Blank lines and lines beginning with ``#`` are ignored. Words are
    upper-cased. Lines whose first token is not purely A-Z are skipped and
    counted in :attr:`Lexicon.skipped`.
    """
    definitions: dict[str, str] = {}
    skipped = 0
    with open(path, encoding="utf-8-sig") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            word, *rest = line.split(None, 1)  # splits on a tab or any spaces
            word = word.upper()
            if not _LETTERS.issuperset(word):
                skipped += 1
                continue
            definitions[word] = rest[0].strip() if rest else ""
    return Lexicon(name=name, definitions=definitions, skipped=skipped)


LOADERS: dict[str, Callable[[Path, str], Lexicon]] = {
    "wordlist": load_wordlist,
}


def load_lexicon(path: Path, name: str, fmt: str = "wordlist") -> Lexicon:
    """Load a lexicon with the loader registered for ``fmt``."""
    try:
        loader = LOADERS[fmt]
    except KeyError:
        known = ", ".join(sorted(LOADERS))
        raise ValueError(f"Unknown dictionary format {fmt!r} (known: {known})") from None
    return loader(path, name)
