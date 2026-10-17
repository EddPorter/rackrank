# How rackrank works

A guided tour of the code, in the order the data flows. Read it alongside the
source: each section names the file it describes. For usage, see the
[README](../README.md).

## The idea

A Scrabble player holds seven tiles. Some seven-letter combinations turn up far
more often than others, so the best use of study time is to learn the words for
the *likeliest* racks first. rackrank answers one question: **for every
seven-letter alphagram, how many ways can the bag deliver it?** Then it sorts by
that, attaches the valid words, and writes flash cards.

```
word list ──► Lexicon ──► group by alphagram ──► score each with draw counts
                                                        │
        Anki files ◄── Cards (ranked, filtered) ◄───────┘
```

An **alphagram** is a word's letters sorted: RETAINS, NASTIER and STAINER all
share `AEINRST`. One alphagram becomes one card, listing all its anagrams.

## 1. Counting draws: `probability.py`

A *draw* is a particular set of physical tiles pulled from the bag. The bag has
nine As, so a rack holding two As can arise in C(9, 2) = 36 ways. For a whole
rack the ways multiply across letters:

```python
total = comb(tiles.get(BLANK, 0), blanks)
for letter, needed in Counter(letters).items():
    total *= comb(tiles.get(letter, 0), needed)
```

For `AEINRST` that is 9 × 12 × 9 × 6 × 6 × 4 × 6 = 839,808 draws, out of
C(100, 7) = 16,007,560,800 possible racks. `draw_count` is that loop; `total_racks`
is the denominator.

**Blanks** make it subtler. With one blank, a rack of `AEINRS?` can spell
`AEINRST` (the blank is the T), but also `AEINRSD` and so on. For a *given*
alphagram, `alphagram_draw_count` tries each distinct choice of letters the
blank could stand for, counts the racks that leaves, and sums them. The racks
are disjoint (different concrete tiles), so adding is correct. The `set(...)`
around `combinations` removes duplicates such as the two As of `AAEINRS`, which
would otherwise be counted twice.

The tile distribution is a plain dict (`STANDARD_TILES`) so a config file can
replace it.

## 2. The word list: `lexicon.py`

`load_wordlist` reads one word per line, optionally followed by a definition,
and returns a `Lexicon`, which is essentially `dict[word, definition]` plus
three questions you can ask of it:

- `alphagrams(7)`: every alphagram of that length, mapped to its sorted words.
  Computed once and cached on the object.
- `front_hooks(word)` / `back_hooks(word)`: the letters that can be added before
  or after `word` to make another valid word. These are worked out by trying
  A to Z against the dictionary itself, so no separate hook table is needed.

Loaders are registered in `LOADERS` by format name. Supporting another file
layout means writing one function and adding it there.

## 3. Ranking: `ranking.py`

`build_cards` is the heart of the program. For the plain mode it is short:

```python
for letters, words in groups.items():
    draws = sum(alphagram_draw_count(letters, tiles, k) for k in spec.blanks)
    if draws:
        scored.append((letters, draws, words))
return _rank(scored, lexicon)
```

`spec.blanks` is a tuple: `(0,)` for no blanks, `(1,)` for one, `(0, 1, 2)` for
`--blanks any`, which sums the three counts. `_rank` sorts by descending draws,
ties broken alphabetically, and numbers the cards from 1.

**Ranks are assigned before any filtering.** `filter_cards` runs afterwards and
only drops cards, so rank 501 is rank 501 whatever else you select. That is
what lets you export "ranks 501-1000, single anagrams only" and still know where
each card sits in the whole list.

A second style, `--front rack`, lists *racks* instead of alphagrams: the
letters held plus a `?` per blank. It builds those by deleting `blanks` letters
from each alphagram in every distinct way, merging the words that share a rack.

`ListSpec` carries everything about *which* list this is (lexicon name, length,
blank mode, style) and derives the names used for decks, note types and tags,
for example the tag `csw24::7::b0::0001-0500`.

## 4. Configuration: `config.py`

A small TOML reader. Relative dictionary paths resolve against the config file's
own directory, so the same config works from any working directory. Tile counts
are validated (`A`-`Z` and `?`, non-negative integers) before use.

## 5. The command line: `cli.py`

`rackrank list` and `rackrank export` share their options, added by
`_add_list_options`. `_build` does the pipeline in one place:

1. load the config, then the lexicon;
2. parse `--blanks`, build the `ListSpec`;
3. `build_cards`, then `filter_cards`;
4. if `--fetch-definitions`, fill in missing definitions and rebuild.

`list` prints the cards; `export` hands them to the writers. Options go *after*
the subcommand (`rackrank export --rank 1-50`) because they belong to it.

## 6. Anki output: `export/`

- `common.py` turns a `Card` into note fields. Racks with four or fewer
  anagrams become **Basic** notes; larger ones become **Cloze** notes, where each
  anagram is hidden behind `{{c1::...}}` so Anki makes one card per anagram
  (`--cloze-mode each`), or all behind one deletion (`all`). Words are
  HTML-escaped; hooks are rendered as `bfry-` and `-s`.
- `tsv.py` writes tab-separated files with Anki's `#notetype`, `#deck` and tag
  headers. The alphagram is always the first field, which Anki uses as the
  note's identity, so re-importing updates notes instead of duplicating them.
- `apkg.py` builds a package with `genanki` (optional dependency). Note-type
  and deck IDs come from a CRC of their names, and note GUIDs from the note type
  plus alphagram, so repeated exports line up with what is already in Anki.
- `templates.py` holds the card HTML and CSS.

## 7. Filling in definitions: `definitions.py`

`--fetch-definitions` looks up only the words in the cards being exported, so a
50-card export costs about a hundred requests, not 280,000.

- `fetch_definition` tries dictionaryapi.dev, then Wiktionary (which covers
  inflections like "plural of atoner"). Neither is Collins.
- Rate limiting raises `RateLimited`; `_fetch_with_backoff` waits 20s, doubling,
  up to five retries per word. A 5xx error skips the word and moves on; five in
  a row stops the run. Skipped words are not remembered, so the next run retries
  them.
- Found definitions are written **back into the word list**, rewriting only the
  lines that had none, through a temporary file and `os.replace` so an
  interruption cannot leave a half-written dictionary.
- Words genuinely not found go in `<wordlist>.nodef` so they are not requested
  again. The write happens in a `finally`, so progress survives Ctrl-C.

## 8. Tests: `tests/`

`conftest.py` defines a tiny invented lexicon, so the suite never needs the
copyrighted dictionary. Tests are small and aimed at one behaviour each:
`test_probability.py` checks the hand-computed 839,808; `test_ranking.py` checks
tie-breaking and that filters leave ranks unchanged; `test_cli.py` runs `main`
end to end on a temporary dictionary; the definition tests inject a fake
`fetch`, so they never touch the network.
