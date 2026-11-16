# humaninput

Find frontend timing bugs by typing like people do, then replay the exact failure.

humaninput generates keystroke timing from a statistical model, with pauses, bursts, typos and corrections. A Playwright test types into a page with one of those streams. Sweep a test across many seeds, and when one fails, the seed replays the same keystrokes with the same timing. See the [demo](demo/index.html) and [Testing with Playwright](testing.md).

**Use it for:** Playwright tests of UI that reacts while someone types: debounced search, autocomplete, per-keystroke validation, input masks. The same event streams can also be rendered as SVG, CSS or terminal typing animations for docs and screencasts.

<p align="center">
  <img src="lead.svg" alt="hunt_and_peck profile, seed 0, typing 'Amsterdam': it types 'Amsy', notices the typo a few letters later, moves back with the arrow keys, replaces the y with a t, moves forward again and finishes the word" width="420">
</p>

<p align="center"><em>The <code>hunt_and_peck</code> profile, seed 0, typing "Amsterdam". It hits y instead of t, notices three letters later and fixes it with the arrow keys. A generated event stream, rendered by the SVG backend.</em></p>

## Core design decision

**The timing engine performs no I/O.** It takes a target string (or a target coordinate) and a profile, and returns a stream of timestamped events. Backends consume that stream and do something with it.

This means the model is unit-testable without touching a screen, the same generated sequence can be replayed into a terminal, an SVG animation, a live browser page, or a JSON file, and statistical validation is possible.

```python
from humaninput import Typist, profiles

t = Typist(profile=profiles.load("touch_typist"), seed=42)
events = t.type("hello world")   # EventStream[KeyEvent], not side effects

for e in events:
    print(e.t_ms, e.action, e.key)   # 0.0 keydown h / 12.4 keyup h / 88.1 keydown e ...
```

Every generator takes a `seed`. Same seed + same profile + same input produces a byte-identical event stream — this is what makes it usable in tests.

## Where to go next

- **[Demo](demo/index.html)** — an automated test and a humaninput seed typing into the same buggy autocomplete.
- **[Quickstart](quickstart.md)** — install, first typing/mouse/touch example, CLI basics.
- **[Testing with Playwright](testing.md)** — `type_into`, seed sweeps, replaying a failing seed.
- **[The model](model.md)** — the statistics behind typing, error injection, mouse movement, and touch.
- **[Profiles](profiles.md)** — full TOML schema, every field with its default and valid range.
- **[Layouts](layouts.md)** — the digraph-classification table format and shipped layouts.
- **[Backends](backends.md)** — every consumer of an `EventStream`, from `terminal` to `browser`/`touch` CDP dispatch.
- **[CLI reference](cli.md)** — every subcommand and flag.

The [README](https://github.com/towa0/humaninput) stays the concise landing page; this site is where the depth lives.
