# humaninput

A statistical model of human input timing — keystrokes, mouse movement, and touch — emitted as a timed event stream.

**Use it for:** recording screencasts and demos where instant text insertion looks wrong, generating typing animations for docs and landing pages, and QA-testing UIs that behave differently under realistic input timing than under instantaneous programmatic input (debounce handling, autocomplete races, per-keystroke validation).

<p align="center">
  <img src="lead.svg" alt="hunt_and_peck profile typing 'realy fast typing looks fake', with a mid-word typo (typk / typkn) caught and corrected back to 'typing'" width="420">
</p>

<p align="center"><em>The <code>hunt_and_peck</code> profile typing a sentence — a real generated event stream, rendered by the SVG backend. No hand-authored timing, no keyframe editing.</em></p>

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

- **[Quickstart](quickstart.md)** — install, first typing/mouse/touch example, CLI basics.
- **[The model](model.md)** — the statistics behind typing, error injection, mouse movement, and touch.
- **[Profiles](profiles.md)** — full TOML schema, every field with its default and valid range.
- **[Layouts](layouts.md)** — the digraph-classification table format and shipped layouts.
- **[Backends](backends.md)** — every consumer of an `EventStream`, from `terminal` to `browser`/`touch` CDP dispatch.
- **[CLI reference](cli.md)** — every subcommand and flag.
- **[Tools](tools.md)** — `click_and_type` and the hotkey-triggered shadow writer.

The [README](https://github.com/towa0/humaninput) stays the concise landing page; this site is where the depth lives.
