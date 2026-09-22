# Layouts

A `Layout` maps each character to its physical key: row, horizontal position, hand, and finger. This table is the **sole input** to digraph classification (see [The model → Digraph classification](model.md#digraph-classification)) and to substitution-error neighbor lookup — alternate layouts are data, not code.

Shipped in `humaninput/layouts/`: `qwerty`, `dvorak`, `colemak`, `azerty`.

```bash
humaninput type "text" --layout dvorak
```

```python
from humaninput.layout import load_layout

layout = load_layout("qwerty")          # or a path to a custom .toml file
layout.classify_digraph("t", "h")        # DigraphClass.ALTERNATING_HAND
layout.neighbors("j", n=6)               # nearest physical keys to 'j'
```

## TOML schema

```toml
name = "qwerty"
display_name = "US QWERTY"

[keys."a"]
row = 2       # 0 = number row, 1 = top row, 2 = home row, 3 = bottom row
col = 1.0     # horizontal position, accounting for physical row stagger
hand = "left" # "left" | "right"
finger = "pinky"  # "pinky" | "ring" | "middle" | "index" | "thumb"

[keys."A"]
row = 2
col = 1.0
hand = "left"
finger = "pinky"
shift = true   # requires Shift to produce this character
base = "a"     # the unshifted character on the same physical key
```

| key | type | required | meaning |
|---|---|---|---|
| `name` | str | yes | short identifier, matches the filename by convention |
| `display_name` | str | no (defaults to `name`) | human-readable name |
| `keys.<char>.row` | int | yes | `0` (number row) – `3` (bottom row) |
| `keys.<char>.col` | float | yes | horizontal position; fractional to represent physical row stagger, used for Euclidean adjacency distance |
| `keys.<char>.hand` | str | yes | `"left"` or `"right"` |
| `keys.<char>.finger` | str | yes | `"pinky"`, `"ring"`, `"middle"`, `"index"`, or `"thumb"` |
| `keys.<char>.shift` | bool | no (default `false`) | whether producing this character requires Shift |
| `keys.<char>.base` | str | no | for a shifted character, the unshifted character sharing its physical key |

Characters not present in the table (rare unicode, etc.) resolve via a lowercase fallback, or are treated as baseline-timed (`same_hand_different_finger`) if still unmapped — see `Layout.key_for`.

## Digraph classification priority

`Layout.classify_digraph(a, b)` (transition typing `a` then `b`) checks, in order:

1. Is `b` a digit? → `to_digit`
2. Is `b` punctuation? → `to_punctuation`
3. Is `a` punctuation? → `from_punctuation`
4. Same physical key (`row`, `col`)? → `same_key`
5. Different hand? → `alternating_hand`
6. Same finger? → `same_finger_different_key`
7. Otherwise → `same_hand_different_finger`

Digits break rhythm hardest, then punctuation, then physical key relationships — matching the digraph-multiplier ordering in [Profiles](profiles.md#digraph_multipliers).
