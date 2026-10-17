# rackrank

Generate ranked Scrabble bingo study lists (seven-letter words) and export them
as Anki decks, most likely racks first. One card per alphagram, with every valid
anagram, its hooks and its definition.

Standard library only, plus [genanki](https://github.com/kerrickstaley/genanki)
if you want `.apkg` files. Requires Python 3.12 or later.

## Setup

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'        # or '.[apkg]' for genanki alone; plain `pip install -e .` for TSV only
pytest
```

## Dictionary

The CSW24 word list is Collins-copyrighted, so it is **not** in this repository,
and `.gitignore` excludes `dictionaries/`, `output/` and `*.apkg` (decks
contain Collins definitions too). Put your file anywhere, for example
`dictionaries/csw24.txt`, with one word per line, optionally followed by a tab
or space and a definition:

```
RETAINS  to keep hold of
SOAPIER
```

Tell rackrank where it is either with `--dict PATH` or in a config file:

```sh
cp config.example.toml config.toml   # git-ignored; edit [dictionary] path
```

Relative paths in the config are resolved against the config file's directory.
Other lexicons (e.g. NWL) work with the same loader; set `name` in the config
so decks, note types and tags are labelled correctly. For a different file
layout, add a function to `rackrank.lexicon.LOADERS` and select it with
`format`.

Front and back hooks are worked out from the word list itself (a hook is a
letter that, added to the word, makes another word in the same lexicon).

## Ranking

Every list is ranked over the whole set of racks for the chosen mode, in
descending order of **draw count**, ties broken alphabetically. Filters are
applied afterwards, so rank 501 stays rank 501 whatever else is selected.

A draw count is the number of distinct sets of physical tiles that give a rack.
For a rack with no blanks it is the product over letters of
C(tiles of that letter in the bag, tiles on the rack). For example AEINRST is
9 × 12 × 9 × 6 × 6 × 4 × 6 = 839,808 of the C(100, 7) = 16,007,560,800
possible racks. The tile distribution is a dict in `rackrank.probability`
(`STANDARD_TILES`) and can be overridden in the config file's `[tiles]` table.

Blank modes (`--blanks`), by default showing the concrete seven letters:

| Option | Meaning |
|---|---|
| `0` | racks with no blanks (default) |
| `1` or `2` | racks with exactly that many blanks that can spell the alphagram. For each *distinct* choice of letters the blanks stand for, the remaining concrete tiles give a different rack; the draw counts are summed, each multiplied by C(blanks in bag, blanks on rack) |
| `any` | the sum of the 0, 1 and 2 blank counts: how often the alphagram can be made from a rack at all, with whatever blanks it holds |

`--front rack` instead lists the *racks* themselves: the letters held plus one
`?` per blank (e.g. `AEINRS?`), with every seven-letter word they can make.
Its draw count is C(2, blanks) × the product for the letters held.

Only seven-letter lists are supported, because a hand holds seven tiles.
Eight-letter lists would need an agreed convention for the tile on the board
and are deliberately left out for now.

## Commands

```sh
# Print the 20 likeliest racks
rackrank list --limit 20

# Racks 501-1000 that have exactly one valid word and a back hook
rackrank list --rank 501-1000 --single-only --back-hook

# Anki text files for the top 500 (writes output/csw24-7-b0-r0001-0500-{basic,cloze}.txt)
rackrank export --rank 1-500

# Same, plus an .apkg
rackrank export --rank 1-500 --format both

# Alphagrams ranked by how often a rack with one blank can make them
rackrank export --blanks 1 --rank 1-500

# Racks of six letters plus a blank
rackrank export --blanks 1 --front rack
```

Run `rackrank list --help` and `rackrank export --help` for every option
(`--config`, `--dict`, `--slice-size`, `--cloze-threshold`, `--cloze-mode`,
`-o/--output-dir`).

## Anki output

Racks with four or fewer anagrams become **Basic** notes; racks with more become
**Cloze** notes (`--cloze-threshold` changes the cut-off). Because they need
different note types, each export writes two files, `…-basic.txt` and
`…-cloze.txt`, and skips either if it would be empty.

| Field | Content |
|---|---|
| `Alphagram` | the sorted letters (always the first field) |
| `Count` | number of valid anagrams |
| `Anagrams` (Basic) / `Text` (Cloze) | each anagram with front hooks (`bfry-`), back hooks (`-s`) and definition |
| `Rank` | position in descending order of probability |
| `Draws` | the draw count |
| tag | rank slice, e.g. `csw24::7::b0::0001-0500` (`--slice-size`, default 500) |

The front of each card shows the letters in capitals followed by the count, for
example `AEGIRST (8)`. In cloze notes, `--cloze-mode each` (the default) hides
one anagram per deletion, so a note yields one card per anagram, as in the
legacy deck; `--cloze-mode all` hides everything behind a single deletion, so
the rack has just one card.

### Importing

The text files carry `#notetype`, `#deck` and tag-column headers (Anki 2.1.54 or
later). They name note types such as `CSW24 7s (Basic)` and `CSW24 7s (Cloze)`,
which must exist. The easiest way to create them is to import the `.apkg` once
(`--format both`); you can then use the text files for later updates. Anki
treats the first field, the alphagram, as the note's identity, so importing again
updates existing notes instead of duplicating them. Each blank mode has its own
note types, so lists with different rankings do not overwrite one another.

The `.apkg` uses a GUID derived from the note type and alphagram for the same
reason.

## Layout

```
src/rackrank/
  probability.py   tile distribution, draw counts, blank handling
  lexicon.py       loaders, alphagram grouping, hooks
  ranking.py       ranked cards and filters
  config.py        TOML configuration
  cli.py           `rackrank list` / `rackrank export`
  export/          common rendering, templates, tsv.py, apkg.py
tests/
```
