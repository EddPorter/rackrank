"""Command-line interface: ``rackrank list`` and ``rackrank export``."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .config import load_config
from .export.common import CLOZE_ALL, CLOZE_EACH, CLOZE_THRESHOLD
from .lexicon import load_lexicon
from .probability import RACK_SIZE, total_racks
from .ranking import (
    ALPHAGRAM,
    RACK,
    Card,
    ListSpec,
    build_cards,
    filter_cards,
    parse_blanks,
    parse_rank_range,
)


def _rank_range(value: str) -> tuple[int, int]:
    try:
        return parse_rank_range(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def _add_list_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, help="TOML config (default: ./config.toml)")
    parser.add_argument("--dict", type=Path, dest="dictionary", help="word list path")
    parser.add_argument(
        "--length", type=int, choices=[RACK_SIZE], default=RACK_SIZE,
        help="word length; only 7 is supported (a hand holds seven tiles)",
    )  # fmt: skip
    parser.add_argument(
        "--blanks", default="0", choices=["0", "1", "2", "any"],
        help="blanks on the rack: exactly 0, 1 or 2, or 'any' to combine them (default 0)",
    )  # fmt: skip
    parser.add_argument(
        "--front", choices=[ALPHAGRAM, RACK], default=ALPHAGRAM,
        help="what a blank-mode card shows: the 7 concrete letters (default), or "
        "'rack': the letters held plus '?' for each blank",
    )  # fmt: skip
    parser.add_argument("--rank", type=_rank_range, metavar="LOW-HIGH", help="e.g. 1-500")
    parser.add_argument("--single-only", action="store_true", help="one valid anagram only")
    parser.add_argument("--front-hook", action="store_true", help="some anagram takes a front hook")
    parser.add_argument("--back-hook", action="store_true", help="some anagram takes a back hook")
    parser.add_argument("--slice-size", type=int, default=500, help="ranks per tag slice (default 500)")


def _build(args: argparse.Namespace) -> tuple[ListSpec, list[Card], list[Card]]:
    config = load_config(args.config)
    path = args.dictionary or config.dictionary_path
    if path is None:
        raise SystemExit("No dictionary: pass --dict or set [dictionary] path in the config")
    if not path.is_file():
        raise SystemExit(f"Dictionary not found: {path}")

    lexicon = load_lexicon(path, config.dictionary_name, config.dictionary_format)
    if lexicon.skipped:
        print(f"Warning: skipped {lexicon.skipped} unreadable dictionary lines", file=sys.stderr)
    fetch = getattr(args, "fetch_definitions", False)
    if fetch and config.dictionary_format != "wordlist":
        raise SystemExit("--fetch-definitions only works with the 'wordlist' format")

    try:
        blanks = parse_blanks(args.blanks, config.tiles)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    if args.front == RACK and len(blanks) != 1:
        raise SystemExit("--front rack needs --blanks 0, 1 or 2, not 'any'")

    spec = ListSpec(config.dictionary_name, args.length, blanks, args.front)
    ranked = build_cards(lexicon, config.tiles, spec)
    selected = filter_cards(
        ranked, args.rank, args.single_only, args.front_hook, args.back_hook
    )
    if fetch:
        from .definitions import fill_definitions

        words = {e.word for card in selected for e in card.entries}
        if fill_definitions(lexicon, words, path):
            ranked = build_cards(lexicon, config.tiles, spec)
            selected = filter_cards(
                ranked, args.rank, args.single_only, args.front_hook, args.back_hook
            )
    args.total = total_racks(config.tiles, RACK_SIZE)
    return spec, ranked, selected


def _list(args: argparse.Namespace) -> int:
    spec, _, cards = _build(args)
    shown = cards[: args.limit] if args.limit else cards
    print(f"# {spec.display_name}: {len(cards)} cards (of {args.total:,} possible racks)")
    for card in shown:
        words = " ".join(e.word for e in card.entries)
        odds = args.total / card.draws
        print(f"{card.rank}\t{card.front}\t{len(card.entries)}\t{card.draws}\t1 in {odds:,.0f}\t{words}")
    return 0


def _export(args: argparse.Namespace) -> int:
    from .export.tsv import write_tsv

    spec, _, cards = _build(args)
    if not cards:
        raise SystemExit("No cards match those filters")

    stem_text = f"{spec.lexicon_name}-{spec.length}-{spec.mode_key}"
    if args.rank:
        stem_text += f"-r{args.rank[0]:04d}-{args.rank[1]:04d}"
    stem = args.output_dir / re.sub(r"[^\w.-]+", "-", stem_text).lower()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    if args.format in ("tsv", "both"):
        written += write_tsv(cards, spec, stem, args.slice_size, args.cloze_threshold, args.cloze_mode)
    if args.format in ("apkg", "both"):
        from .export.apkg import write_apkg

        written.append(write_apkg(cards, spec, stem, args.slice_size, args.cloze_threshold, args.cloze_mode))
    for path in written:
        print(path)
    print(f"{len(cards)} cards exported")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rackrank", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list", help="print a ranked list")
    _add_list_options(list_parser)
    list_parser.add_argument("--limit", type=int, help="show only the first N matching cards")
    list_parser.set_defaults(run=_list)

    export_parser = commands.add_parser("export", help="write Anki files")
    _add_list_options(export_parser)
    export_parser.add_argument("--format", choices=["tsv", "apkg", "both"], default="tsv")
    export_parser.add_argument("-o", "--output-dir", type=Path, default=Path("output"))
    export_parser.add_argument(
        "--cloze-threshold", type=int, default=CLOZE_THRESHOLD,
        help=f"racks with more anagrams than this become cloze notes (default {CLOZE_THRESHOLD})",
    )  # fmt: skip
    export_parser.add_argument(
        "--cloze-mode", choices=[CLOZE_EACH, CLOZE_ALL], default=CLOZE_EACH,
        help="'each': one deletion per anagram, so one card per anagram (default); "
        "'all': hide every anagram at once, so a single card per rack",
    )  # fmt: skip
    export_parser.add_argument(
        "--fetch-definitions", action="store_true",
        help="look up missing definitions online and save them into the word list",
    )  # fmt: skip
    export_parser.set_defaults(run=_export)

    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
