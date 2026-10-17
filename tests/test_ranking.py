import pytest

from rackrank.probability import STANDARD_TILES
from rackrank.ranking import (
    RACK,
    ListSpec,
    build_cards,
    filter_cards,
    parse_blanks,
    parse_rank_range,
)


def cards_for(lexicon, **kwargs):
    return build_cards(lexicon, STANDARD_TILES, ListSpec("TEST", **kwargs))


def test_ranked_by_descending_draws(lexicon):
    cards = cards_for(lexicon)
    assert [c.rank for c in cards] == list(range(1, len(cards) + 1))
    assert [c.draws for c in cards] == sorted((c.draws for c in cards), reverse=True)
    assert cards[0].front == "AEINRST"
    assert cards[0].draws == 839_808


def test_each_alphagram_is_one_card_with_all_anagrams(lexicon):
    cards = {c.front: c for c in cards_for(lexicon)}
    assert [e.word for e in cards["AEINRST"].entries] == [
        "NASTIER", "RETAINS", "RETSINA", "STAINER", "STEARIN",
    ]  # fmt: skip


def test_ties_are_broken_alphabetically():
    from rackrank.lexicon import Lexicon

    lexicon = Lexicon("T", {"ABCDEFG": "", "BCDEFGH": ""})
    bag = {c: 1 for c in "ABCDEFGH"}
    cards = build_cards(lexicon, bag, ListSpec("T"))
    assert [c.front for c in cards] == ["ABCDEFG", "BCDEFGH"]


def test_rank_range_keeps_global_ranks(lexicon):
    cards = cards_for(lexicon)
    selected = filter_cards(cards, rank_range=(2, 3))
    assert [c.rank for c in selected] == [2, 3]


def test_single_only(lexicon):
    selected = filter_cards(cards_for(lexicon), single_only=True)
    assert selected and all(len(c.entries) == 1 for c in selected)


def test_hook_filters(lexicon):
    cards = cards_for(lexicon)
    with_front = {c.front for c in filter_cards(cards, front_hook=True)}
    with_back = {c.front for c in filter_cards(cards, back_hook=True)}
    assert with_front == {"AEIOPRS"}  # BSOAPIER
    assert with_back == {"AEIOPRS"}  # SOAPIERS


def test_blank_modes_change_the_ranking_values(lexicon):
    none = {c.front: c.draws for c in cards_for(lexicon)}
    one = {c.front: c.draws for c in cards_for(lexicon, blanks=(1,))}
    both = {c.front: c.draws for c in cards_for(lexicon, blanks=(0, 1, 2))}
    assert one["AEINRST"] > none["AEINRST"]
    assert both["AEINRST"] > one["AEINRST"]


def test_unobtainable_racks_are_dropped(lexicon):
    assert "GLOOOYZ" in {c.front for c in cards_for(lexicon)}
    no_z = {k: v for k, v in STANDARD_TILES.items() if k != "Z"}
    cards = build_cards(lexicon, no_z, ListSpec("TEST"))
    assert "GLOOOYZ" not in {c.front for c in cards}


def test_rack_style_shows_letters_held_plus_blank(lexicon):
    cards = cards_for(lexicon, blanks=(1,), style=RACK)
    fronts = {c.front for c in cards}
    assert "AEINRS?" in fronts  # RETAINS etc. minus the T
    card = next(c for c in cards if c.front == "AEINRS?")
    assert card.draws == 2 * 9 * 12 * 9 * 6 * 6 * 4
    assert {e.word for e in card.entries} >= {"RETAINS", "RETSINA"}


def test_list_spec_names_and_tags():
    spec = ListSpec("CSW24", blanks=(1,))
    assert spec.display_name == "CSW24 7s, 1 blank"
    assert spec.slice_tag(1, 500) == "csw24::7::b1::0001-0500"
    assert spec.slice_tag(500, 500) == "csw24::7::b1::0001-0500"
    assert spec.slice_tag(501, 500) == "csw24::7::b1::0501-1000"
    assert ListSpec("CSW24").display_name == "CSW24 7s"
    assert ListSpec("CSW24", blanks=(0, 1, 2)).mode_key == "ball"


def test_parse_helpers():
    assert parse_rank_range("501-1000") == (501, 1000)
    assert parse_rank_range("7") == (7, 7)
    with pytest.raises(ValueError):
        parse_rank_range("10-5")
    assert parse_blanks("any", STANDARD_TILES) == (0, 1, 2)
    assert parse_blanks("1", STANDARD_TILES) == (1,)
    with pytest.raises(ValueError):
        parse_blanks("3", STANDARD_TILES)
