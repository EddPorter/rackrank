import pytest

from conftest import WORDS
from rackrank.cli import main


@pytest.fixture
def dictionary(tmp_path):
    path = tmp_path / "dict.txt"
    path.write_text("\n".join(f"{w} {d}".strip() for w, d in WORDS.items()) + "\n")
    return path


def test_list_prints_most_likely_first(dictionary, capsys):
    assert main(["list", "--dict", str(dictionary), "--limit", "2"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("# CSW24 7s: ")
    assert lines[1].split("\t")[:4] == ["1", "AEINRST", "5", "839808"]


def test_export_writes_files_named_for_the_list(dictionary, tmp_path, capsys):
    out = tmp_path / "decks"
    main(["export", "--dict", str(dictionary), "-o", str(out), "--rank", "1-1"])
    assert sorted(p.name for p in out.iterdir()) == ["csw24-7-b0-r0001-0001-cloze.txt"]


def test_export_with_config_relative_dictionary(dictionary, tmp_path, capsys):
    config = tmp_path / "config.toml"
    config.write_text('[dictionary]\npath = "dict.txt"\nname = "NWL"\n')
    out = tmp_path / "decks"
    main(["export", "--config", str(config), "-o", str(out), "--blanks", "1"])
    assert (out / "nwl-7-b1-basic.txt").exists()


def test_rack_front_cannot_combine_blank_counts(dictionary):
    with pytest.raises(SystemExit):
        main(["list", "--dict", str(dictionary), "--blanks", "any", "--front", "rack"])


def test_missing_dictionary_is_a_clear_error(tmp_path):
    with pytest.raises(SystemExit, match="Dictionary not found"):
        main(["list", "--dict", str(tmp_path / "nope.txt")])
