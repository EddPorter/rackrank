"""Configuration: dictionary location and tile distribution."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .probability import STANDARD_TILES, validate_tiles

DEFAULT_CONFIG = Path("config.toml")


@dataclass
class Config:
    dictionary_path: Path | None = None
    dictionary_name: str = "CSW24"
    dictionary_format: str = "wordlist"
    tiles: dict[str, int] = field(default_factory=lambda: dict(STANDARD_TILES))


def load_config(path: Path | None) -> Config:
    """Read a TOML config file.

    With no ``path``, ``config.toml`` in the current directory is used if it
    exists; otherwise the defaults apply. Relative dictionary paths are
    resolved against the directory holding the config file.
    """
    if path is None:
        if not DEFAULT_CONFIG.is_file():
            return Config()
        path = DEFAULT_CONFIG
    with open(path, "rb") as handle:
        data = tomllib.load(handle)

    config = Config()
    dictionary = data.get("dictionary", {})
    if "path" in dictionary:
        config.dictionary_path = (path.parent / dictionary["path"]).resolve()
    config.dictionary_name = dictionary.get("name", config.dictionary_name)
    config.dictionary_format = dictionary.get("format", config.dictionary_format)
    if "tiles" in data:
        config.tiles = validate_tiles(data["tiles"])
    return config
