"""One-off generator for alternate layout TOML files, reusing the physical
key grid (row, col, hand, finger) defined in qwerty.toml and remapping
characters onto that grid per published layout charts. Not part of the
package; run once to produce humaninput/layouts/{dvorak,colemak,azerty}.toml.
"""

from __future__ import annotations

import pathlib

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAYOUTS = ROOT / "humaninput" / "layouts"

with open(LAYOUTS / "qwerty.toml", "rb") as f:
    qwerty = tomllib.load(f)

grid_by_qwerty_char: dict[str, dict] = {}
for ch, info in qwerty["keys"].items():
    if info.get("shift"):
        continue
    grid_by_qwerty_char[ch] = info

NUMBER_ROW = list("`1234567890-=")
TOP_ROW = list("qwertyuiop[]\\")
HOME_ROW = list("asdfghjkl;'")
BOTTOM_ROW = list("zxcvbnm,./")

SHIFT_OF_QWERTY = {
    "`": "~", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^",
    "7": "&", "8": "*", "9": "(", "0": ")", "-": "_", "=": "+",
    "[": "{", "]": "}", "\\": "|", ";": ":", "'": "\"", ",": "<", ".": ">", "/": "?",
}


def build_layout(name: str, display_name: str, mapping: dict[str, str], shift_map: dict[str, str]) -> dict:
    """mapping: qwerty physical-position char -> new char for that position.
    shift_map: new unshifted char -> new shifted char (for symbols only;
    letters are handled automatically via upper()).
    """
    keys: dict[str, dict] = {}
    for qch, new_ch in mapping.items():
        base_info = grid_by_qwerty_char[qch]
        entry = {"row": base_info["row"], "col": base_info["col"], "hand": base_info["hand"], "finger": base_info["finger"]}
        keys[new_ch] = dict(entry)
        if new_ch.isalpha():
            shifted = new_ch.upper()
            if shifted != new_ch:
                s = dict(entry)
                s["shift"] = True
                s["base"] = new_ch
                keys[shifted] = s
        elif new_ch in shift_map:
            shifted = shift_map[new_ch]
            s = dict(entry)
            s["shift"] = True
            s["base"] = new_ch
            keys[shifted] = s
    keys[" "] = dict(grid_by_qwerty_char[" "])
    return {"name": name, "display_name": display_name, "keys": keys}


def dump_toml(layout: dict) -> str:
    lines = [f'name = "{layout["name"]}"', f'display_name = "{layout["display_name"]}"', ""]

    def esc(ch: str) -> str:
        if ch == "\\":
            return "\\\\"
        if ch == '"':
            return '\\"'
        return ch

    for ch, info in layout["keys"].items():
        lines.append(f'[keys."{esc(ch)}"]')
        lines.append(f'row = {info["row"]}')
        lines.append(f'col = {info["col"]}')
        lines.append(f'hand = "{info["hand"]}"')
        lines.append(f'finger = "{info["finger"]}"')
        if info.get("shift"):
            lines.append("shift = true")
            lines.append(f'base = "{esc(info["base"])}"')
        lines.append("")
    return "\n".join(lines)


dvorak_number = list("`1234567890[]")
dvorak_top = list("',.pyfgcrl/=\\")
dvorak_home = list("aoeuidhtns-")
dvorak_bottom = list(";qjkxbmwvz")

dvorak_mapping = {}
dvorak_mapping.update(dict(zip(NUMBER_ROW, dvorak_number)))
dvorak_mapping.update(dict(zip(TOP_ROW, dvorak_top)))
dvorak_mapping.update(dict(zip(HOME_ROW, dvorak_home)))
dvorak_mapping.update(dict(zip(BOTTOM_ROW, dvorak_bottom)))

dvorak_shift_map = {
    "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
    "[": "{", "]": "}", "'": "\"", ",": "<", ".": ">", "/": "?", "=": "+", "\\": "|", "-": "_",
}

dvorak = build_layout("dvorak", "US Dvorak", dvorak_mapping, dvorak_shift_map)

colemak_number = list("`1234567890-=")
colemak_top = list("qwfpgjluy;[]\\")
colemak_home = list("arstdhneio'")
colemak_bottom = list("zxcvbkm,./")

colemak_mapping = {}
colemak_mapping.update(dict(zip(NUMBER_ROW, colemak_number)))
colemak_mapping.update(dict(zip(TOP_ROW, colemak_top)))
colemak_mapping.update(dict(zip(HOME_ROW, colemak_home)))
colemak_mapping.update(dict(zip(BOTTOM_ROW, colemak_bottom)))

colemak_shift_map = dict(SHIFT_OF_QWERTY)

colemak = build_layout("colemak", "Colemak", colemak_mapping, colemak_shift_map)

azerty_number_unshifted = list("²&é\"'(-è_çà)=")
azerty_number_shifted = {
    "1": "&", "2": "é", "3": '"', "4": "'", "5": "(", "6": "-", "7": "è", "8": "_",
    "9": "ç", "0": "à", "-": ")", "=": "=",
}

azerty_top = list("azertyuiop^$\\")
azerty_home = list("qsdfghjklmù")
azerty_bottom = list("wxcvbn,;:!")

azerty_mapping = {}
azerty_mapping.update(dict(zip(TOP_ROW, azerty_top)))
azerty_mapping.update(dict(zip(HOME_ROW, azerty_home)))
azerty_mapping.update(dict(zip(BOTTOM_ROW, azerty_bottom)))

azerty_shift_map = {
    "^": "¨", "$": "£", "\\": "μ", "ù": "%",
    ",": "?", ";": ".", ":": "/", "!": "§",
}

azerty = build_layout("azerty", "French AZERTY", azerty_mapping, azerty_shift_map)

digit_symbols = {"1": "&", "2": "é", "3": '"', "4": "'", "5": "(", "6": "-", "7": "è", "8": "_", "9": "ç", "0": "à"}
for qch, sym in digit_symbols.items():
    base_info = grid_by_qwerty_char[qch]
    entry = {"row": base_info["row"], "col": base_info["col"], "hand": base_info["hand"], "finger": base_info["finger"]}
    azerty["keys"][sym] = dict(entry)
    shifted = dict(entry)
    shifted["shift"] = True
    shifted["base"] = sym
    azerty["keys"][qch] = shifted
grave_info = grid_by_qwerty_char["`"]
azerty["keys"]["²"] = {"row": grave_info["row"], "col": grave_info["col"], "hand": grave_info["hand"], "finger": grave_info["finger"]}
dash_info = grid_by_qwerty_char["-"]
azerty["keys"][")"] = {"row": dash_info["row"], "col": dash_info["col"], "hand": dash_info["hand"], "finger": dash_info["finger"]}
azerty["keys"]["°"] = {"row": dash_info["row"], "col": dash_info["col"], "hand": dash_info["hand"], "finger": dash_info["finger"], "shift": True, "base": ")"}
eq_info = grid_by_qwerty_char["="]
azerty["keys"]["="] = {"row": eq_info["row"], "col": eq_info["col"], "hand": eq_info["hand"], "finger": eq_info["finger"]}
azerty["keys"]["+"] = {"row": eq_info["row"], "col": eq_info["col"], "hand": eq_info["hand"], "finger": eq_info["finger"], "shift": True, "base": "="}

azerty["keys"][" "] = dict(grid_by_qwerty_char[" "])

for layout in (dvorak, colemak, azerty):
    out_path = LAYOUTS / f"{layout['name']}.toml"
    out_path.write_text(dump_toml(layout), encoding="utf-8")
    print(f"wrote {out_path}")
