"""Anki card templates and styling for the generated note types."""

CSS = """\
.card { font-family: Georgia, serif; font-size: 20px; text-align: center; }
.alphagram { font-family: Menlo, Consolas, monospace; font-size: 2em;
  letter-spacing: 0.2em; text-transform: uppercase; }
.count { color: #888; }
.word { font-weight: bold; text-transform: uppercase; }
.hook { color: #2a6; font-family: Menlo, Consolas, monospace; }
.definition { color: #555; font-size: 0.85em; }
.meta { color: #999; font-size: 0.7em; margin-top: 1.5em; }
"""

_FRONT = (
    '<div class="alphagram">{{Alphagram}}</div>'
    '<div class="count">({{Count}})</div>'
)
_META = '<div class="meta">Rank {{Rank}} &middot; {{Draws}} draws</div>'

BASIC_QFMT = _FRONT
BASIC_AFMT = "{{FrontSide}}<hr id=answer>{{Anagrams}}" + _META

CLOZE_QFMT = _FRONT + "<br>{{cloze:Text}}"
CLOZE_AFMT = _FRONT + "<br>{{cloze:Text}}" + _META
