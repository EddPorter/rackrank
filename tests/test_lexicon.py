from rackrank.lexicon import alphagram, load_lexicon, load_wordlist


def test_alphagram_sorts_letters():
    assert alphagram("RETAINS") == "AEINRST"


def test_loader_handles_tabs_spaces_and_bare_words(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text(
        "﻿# comment\ncat\ta small feline\nSCAT some definition here\nCATS\n\n9bad line\n",
        encoding="utf-8",
    )
    lexicon = load_wordlist(path, "T")
    assert lexicon.definitions == {
        "CAT": "a small feline",
        "SCAT": "some definition here",
        "CATS": "",
    }
    assert lexicon.skipped == 1


def test_unknown_format_is_reported(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="Unknown dictionary format"):
        load_lexicon(tmp_path / "x", "T", "nonsense")


def test_alphagrams_group_anagrams(lexicon):
    groups = lexicon.alphagrams(7)
    assert groups["AEINRST"] == ["NASTIER", "RETAINS", "RETSINA", "STAINER", "STEARIN"]
    assert groups["AEIOPRS"] == ["SOAPIER"]
    assert "CAT" not in {w for ws in groups.values() for w in ws}


def test_hooks_come_from_the_lexicon(lexicon):
    assert lexicon.front_hooks("CAT") == "s"
    assert lexicon.back_hooks("CAT") == "s"
    assert lexicon.front_hooks("SOAPIER") == "b"
    assert lexicon.back_hooks("SOAPIER") == "s"
    assert lexicon.front_hooks("ABOUNDS") == ""
