import pytest

from rackrank.lexicon import Lexicon

# A small invented lexicon. The definitions are made up; the real, copyrighted
# dictionary is never needed to run the tests. BSOAPIER and ASTAINER are
# deliberately fake words that supply a front hook to SOAPIER and STAINER.
WORDS = {
    "RETAINS": "first",
    "RETSINA": "second & <third>",
    "STAINER": "fourth",
    "STEARIN": "fifth",
    "NASTIER": "sixth",
    "SOAPIER": "",
    "BSOAPIER": "",
    "SOAPIERS": "",
    "ABOUNDS": "",
    "ZOOLOGY": "",
    "CAT": "",
    "SCAT": "",
    "CATS": "",
}


@pytest.fixture
def lexicon() -> Lexicon:
    return Lexicon(name="TEST", definitions=dict(WORDS))
