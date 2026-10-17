"""Look up missing definitions online and cache them in the word list.

Definitions come from the free dictionaryapi.dev service, falling back to
Wiktionary (which also covers inflected forms such as "retains"). Neither is
Collins, so some Scrabble-only words will not be found. Found definitions are
written back into the word-list file; words that were not found are recorded in
a ``<wordlist>.nodef`` file so they are not requested again.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path

from .lexicon import Lexicon

API = "https://api.dictionaryapi.dev/api/v2/entries/en/"
WIKTIONARY = "https://en.wiktionary.org/api/rest_v1/page/definition/"
DELAY = 0.7  # seconds between requests; the service allows about 450 per 5 minutes


class RateLimited(Exception):
    """The service asked us to slow down."""


def _get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "rackrank"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        if error.code == 429:
            raise RateLimited from None
        raise


def _clean(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", text)).split())


def _dictionaryapi(word: str) -> str | None:
    for entry in _get_json(API + word.lower()) or []:
        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                text = _clean(definition.get("definition", ""))
                if text:
                    part = meaning.get("partOfSpeech")
                    return f"({part.lower()}) {text}" if part else text
    return None


def _wiktionary(word: str) -> str | None:
    for entry in (_get_json(WIKTIONARY + word.lower()) or {}).get("en", []):
        for definition in entry.get("definitions", []):
            text = _clean(definition.get("definition", ""))
            if text:
                part = entry.get("partOfSpeech")
                return f"({part.lower()}) {text}" if part else text
    return None


def fetch_definition(word: str) -> str | None:
    """The first definition of ``word`` as one line, or None if not found."""
    return _dictionaryapi(word) or _wiktionary(word)


def misses_path(path: Path) -> Path:
    return path.with_name(path.name + ".nodef")


def _read_misses(path: Path) -> set[str]:
    try:
        return set(misses_path(path).read_text(encoding="utf-8").split())
    except FileNotFoundError:
        return set()


def _write_atomic(path: Path, text: str) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def _store(path: Path, found: dict[str, str], misses: set[str]) -> None:
    if found:
        lines = []
        with open(path, encoding="utf-8-sig") as handle:
            for raw in handle:
                parts = raw.split(None, 1)
                word = parts[0].upper() if parts else ""
                if word in found and len(parts) == 1:
                    raw = f"{parts[0]}\t{found[word]}\n"
                lines.append(raw if raw.endswith("\n") else raw + "\n")
        _write_atomic(path, "".join(lines))
    if misses:
        _write_atomic(misses_path(path), "\n".join(sorted(misses)) + "\n")


def fill_definitions(
    lexicon: Lexicon,
    words: Iterable[str],
    path: Path,
    fetch: Callable[[str], str | None] = fetch_definition,
    delay: float = DELAY,
) -> int:
    """Fetch definitions for ``words`` that lack one; returns how many were found.

    Updates ``lexicon`` and ``path`` (also on interruption or rate limiting).
    """
    misses = _read_misses(path)
    todo = sorted({w for w in words if not lexicon.definitions.get(w) and w not in misses})
    if not todo:
        return 0
    print(f"Looking up {len(todo)} definitions...", file=sys.stderr)
    found: dict[str, str] = {}
    new_misses = set(misses)
    failed = 0  # words skipped after a service error (not recorded as misses)
    streak = 0
    try:
        for index, word in enumerate(todo):
            if index:
                time.sleep(delay)
            try:
                definition = fetch(word)
            except RateLimited:
                print("Rate limited; stopping. Run again later to continue.", file=sys.stderr)
                break
            except (urllib.error.URLError, TimeoutError) as error:
                failed += 1
                streak += 1
                print(f"Lookup failed for {word} ({error}); skipped.", file=sys.stderr)
                if streak >= 5:
                    print("Too many failures in a row; stopping.", file=sys.stderr)
                    break
                continue
            streak = 0
            if definition:
                found[word] = definition
                lexicon.definitions[word] = definition
            else:
                new_misses.add(word)
    finally:
        _store(path, found, new_misses if new_misses != misses else set())
    print(
        f"Found {len(found)} of {len(todo)}; {len(new_misses) - len(misses)} not found "
        f"(recorded in {misses_path(path).name}); {failed} failed and will be retried",
        file=sys.stderr,
    )
    return len(found)
