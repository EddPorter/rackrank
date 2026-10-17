import pytest

from rackrank.export.common import basic_fields, cloze_fields
from rackrank.export.tsv import write_tsv
from rackrank.probability import STANDARD_TILES
from rackrank.ranking import ListSpec, build_cards


@pytest.fixture
def spec():
    return ListSpec("TEST")


@pytest.fixture
def cards(lexicon, spec):
    return build_cards(lexicon, STANDARD_TILES, spec)


def read(path):
    return path.read_text(encoding="utf-8").splitlines()


def test_basic_fields_separate_the_count_and_escape_html(cards):
    card = next(c for c in cards if c.front == "AEINRST")
    fields = basic_fields(card)
    assert fields[:2] == ["AEINRST", "5"]
    assert fields[3:] == ["1", "839,808"]
    assert "second &amp; &lt;third&gt;" in fields[2]


def test_cloze_each_numbers_every_anagram(cards):
    card = next(c for c in cards if c.front == "AEINRST")
    text = cloze_fields(card)[2]
    assert all("{{c%d::" % n in text for n in range(1, 6))


def test_tsv_writes_two_files_split_on_the_threshold(cards, spec, tmp_path):
    paths = write_tsv(cards, spec, tmp_path / "out", slice_size=500)
    assert sorted(p.name for p in paths) == ["out-basic.txt", "out-cloze.txt"]

    cloze = read(tmp_path / "out-cloze.txt")
    assert cloze[:5] == [
        "#separator:tab",
        "#html:true",
        "#notetype:TEST 7s (Cloze)",
        "#deck:TEST 7s",
        "#tags column:6",
    ]
    rows = [line.split("\t") for line in cloze[5:]]
    assert [r[0] for r in rows] == ["AEINRST"]
    assert rows[0][1] == "5" and rows[0][5] == "test::7::b0::0001-0500"

    basic = [line.split("\t") for line in read(tmp_path / "out-basic.txt")[5:]]
    assert {r[0] for r in basic} == {"AEIOPRS", "ABDNOSU", "GLOOOYZ"}
    assert all(len(r) == 6 for r in basic)


def test_tsv_skips_a_file_with_no_notes(cards, spec, tmp_path):
    single = [c for c in cards if len(c.entries) == 1]
    paths = write_tsv(single, spec, tmp_path / "out", slice_size=500)
    assert [p.name for p in paths] == ["out-basic.txt"]


def test_tsv_rows_are_ordered_most_likely_first(cards, spec, tmp_path):
    write_tsv(cards, spec, tmp_path / "out", slice_size=500, cloze_threshold=0)
    ranks = [int(line.split("\t")[3]) for line in read(tmp_path / "out-cloze.txt")[5:]]
    assert ranks == sorted(ranks)


def test_apkg_has_stable_guids(cards, spec, tmp_path):
    genanki = pytest.importorskip("genanki")
    from rackrank.export.apkg import write_apkg

    first = write_apkg(cards, spec, tmp_path / "a", slice_size=500)
    second = write_apkg(cards, spec, tmp_path / "b", slice_size=500)
    assert first.name == "a.apkg" and first.stat().st_size > 0

    import sqlite3
    import zipfile

    def guids(path):
        with zipfile.ZipFile(path) as package:
            package.extract("collection.anki2", tmp_path / path.stem)
        db = sqlite3.connect(tmp_path / path.stem / "collection.anki2")
        return sorted(row[0] for row in db.execute("select guid from notes"))

    assert guids(first) == guids(second)
    assert len(guids(first)) == len(cards)
    assert genanki.guid_for("TEST 7s (Cloze)", "AEINRST") in guids(first)
