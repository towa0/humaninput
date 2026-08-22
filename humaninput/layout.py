"""Keyboard layout tables and digraph classification.

A `Layout` is loaded from a TOML file in `humaninput/layouts/` (or a user
supplied path) and maps each character to the physical key that produces
it: row, horizontal position, hand, and finger. This is the sole input to
digraph classification, which drives inter-key interval timing, and to
substitution-error neighbor lookup.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from enum import Enum
from functools import cache

from humaninput import _toml

_LAYOUTS_DIR = pathlib.Path(__file__).parent / "layouts"


class DigraphClass(str, Enum):
    SAME_KEY = "same_key"
    ALTERNATING_HAND = "alternating_hand"
    SAME_HAND_DIFFERENT_FINGER = "same_hand_different_finger"
    SAME_FINGER_DIFFERENT_KEY = "same_finger_different_key"
    TO_PUNCTUATION = "to_punctuation"
    FROM_PUNCTUATION = "from_punctuation"
    TO_DIGIT = "to_digit"


@dataclass(frozen=True, slots=True)
class KeyInfo:
    char: str
    row: int
    col: float
    hand: str
    finger: str
    shift: bool = False
    base: str | None = None


class Layout:
    def __init__(self, name: str, display_name: str, keys: dict[str, KeyInfo]):
        self.name = name
        self.display_name = display_name
        self.keys = keys

    @classmethod
    def load(cls, name_or_path: str) -> Layout:
        path = pathlib.Path(name_or_path)
        if not path.suffix:
            path = _LAYOUTS_DIR / f"{name_or_path}.toml"
        if not path.exists():
            available = sorted(p.stem for p in _LAYOUTS_DIR.glob("*.toml"))
            raise FileNotFoundError(f"layout {name_or_path!r} not found. Available: {available}")
        with open(path, "rb") as f:
            data = _toml.load(f)
        keys = {}
        for ch, info in data["keys"].items():
            keys[ch] = KeyInfo(
                char=ch,
                row=info["row"],
                col=info["col"],
                hand=info["hand"],
                finger=info["finger"],
                shift=info.get("shift", False),
                base=info.get("base"),
            )
        return cls(data["name"], data.get("display_name", data["name"]), keys)

    def key_for(self, char: str) -> KeyInfo | None:
        """Return the physical key info for a character, falling back to a
        lowercase lookup so unknown-case letters still resolve. Unmapped
        characters (rare unicode, etc.) return None and are treated as
        baseline-timed by the caller.
        """
        if char in self.keys:
            return self.keys[char]
        lower = char.lower()
        if lower in self.keys:
            return self.keys[lower]
        return None

    def physical_position(self, char: str) -> tuple[int, float] | None:
        info = self.key_for(char)
        if info is None:
            return None
        return (info.row, info.col)

    def distance(self, a: str, b: str) -> float | None:
        pa, pb = self.physical_position(a), self.physical_position(b)
        if pa is None or pb is None:
            return None
        return ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5

    @cache
    def _neighbors_cached(self, char: str, n: int) -> tuple[str, ...]:
        target = self.physical_position(char)
        if target is None:
            return ()
        dists = []
        for ch, info in self.keys.items():
            if ch == char or info.finger == "thumb":
                continue
            d = ((info.row - target[0]) ** 2 + (info.col - target[1]) ** 2) ** 0.5
            dists.append((d, ch))
        dists.sort(key=lambda t: t[0])
        return tuple(ch for _, ch in dists[:n])

    def neighbors(self, char: str, n: int = 6) -> list[str]:
        """Nearest physical keys to `char`, closest first. Used to weight
        substitution-error targets toward physically adjacent keys.
        """
        return list(self._neighbors_cached(char, n))

    @staticmethod
    def is_digit(char: str) -> bool:
        return char.isdigit()

    @staticmethod
    def is_punctuation(char: str) -> bool:
        return not char.isalnum() and not char.isspace() and char != ""

    def classify_digraph(self, a: str, b: str) -> DigraphClass:
        """Classify the transition typing `a` then `b`. Priority: digits
        break rhythm hardest, then punctuation, then physical key
        relationships (same key / hand-and-finger overlap).
        """
        if self.is_digit(b):
            return DigraphClass.TO_DIGIT
        if self.is_punctuation(b):
            return DigraphClass.TO_PUNCTUATION
        if self.is_punctuation(a):
            return DigraphClass.FROM_PUNCTUATION

        ka, kb = self.key_for(a), self.key_for(b)
        if ka is None or kb is None:
            return DigraphClass.SAME_HAND_DIFFERENT_FINGER

        if (ka.row, ka.col) == (kb.row, kb.col):
            return DigraphClass.SAME_KEY
        if ka.hand != kb.hand:
            return DigraphClass.ALTERNATING_HAND
        if ka.finger == kb.finger:
            return DigraphClass.SAME_FINGER_DIFFERENT_KEY
        return DigraphClass.SAME_HAND_DIFFERENT_FINGER


@cache
def load_layout(name_or_path: str) -> Layout:
    return Layout.load(name_or_path)


def available_layouts() -> list[str]:
    return sorted(p.stem for p in _LAYOUTS_DIR.glob("*.toml"))
