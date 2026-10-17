from itertools import combinations_with_replacement
from math import comb

import pytest

from rackrank.probability import (
    BLANK,
    STANDARD_TILES,
    alphagram_draw_count,
    draw_count,
    total_racks,
    validate_tiles,
)


def test_standard_distribution_has_100_tiles():
    assert sum(STANDARD_TILES.values()) == 100


def test_total_racks_is_c_100_7():
    assert total_racks(STANDARD_TILES) == comb(100, 7) == 16_007_560_800


def test_aeinrst_hand_checked_value():
    # 9 * 12 * 9 * 6 * 6 * 4 * 6 = 839,808
    assert draw_count("AEINRST", STANDARD_TILES) == 839_808


def test_repeated_letters_use_binomials():
    # Two Es from twelve: C(12, 2) = 66; one A from nine: 9
    assert draw_count("AEE", STANDARD_TILES) == 9 * 66


def test_impossible_rack_has_no_draws():
    assert draw_count("QQ", STANDARD_TILES) == 0


def test_draw_counts_over_every_rack_sum_to_total():
    bag = {"A": 2, "B": 1, "C": 3, BLANK: 2}
    letters = [t for t in bag if t != BLANK]
    size = 4
    total = 0
    for blanks in range(0, bag[BLANK] + 1):
        for rack in combinations_with_replacement(letters, size - blanks):
            total += draw_count(rack, bag, blanks)
    assert total == comb(sum(bag.values()), size)


def test_one_blank_alphagram_sums_over_distinct_substitutions():
    bag = {"A": 2, "B": 1, "C": 1, BLANK: 1}
    # AAB with one blank: blank=A leaves AB (2*1*1 = 2); blank=B leaves AA (1).
    # The two As give the same rack, so they must be counted once.
    assert alphagram_draw_count("AAB", bag, blanks=1) == 3


def test_one_blank_matches_hand_calculation_on_standard_bag():
    expected = 0
    for omitted in "AEINRST":
        rest = "AEINRST".replace(omitted, "", 1)
        expected += 2 * draw_count(rest, STANDARD_TILES)
    assert alphagram_draw_count("AEINRST", STANDARD_TILES, blanks=1) == expected


def test_two_blanks_choose_both_blanks_from_bag():
    bag = {"A": 1, "B": 1, "C": 1, BLANK: 2}
    # ABC with two blanks: three ways to keep one letter, each 1 draw,
    # and C(2, 2) = 1 way to take both blanks.
    assert alphagram_draw_count("ABC", bag, blanks=2) == 3


def test_blank_request_beyond_bag_gives_zero():
    bag = {"A": 1, "B": 1, BLANK: 1}
    assert alphagram_draw_count("AB", bag, blanks=2) == 0


@pytest.mark.parametrize("bad", [{"AA": 1}, {"a": 1}, {"A": -1}, {"A": True}, {"1": 1}])
def test_validate_tiles_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        validate_tiles(bad)
