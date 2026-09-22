# Quickstart

## Install

```bash
pip install humaninput              # core: numpy only
pip install humaninput[pynput]      # + real OS keyboard/mouse control
pip install humaninput[playwright]  # + browser/touch backends (BYO Page)
pip install humaninput[matplotlib]  # + validation plots
```

`import humaninput` never requires `pynput`, `playwright`, or `matplotlib` — each is a lazily-imported optional dependency, only touched by the backend that needs it.

## Typing

```python
from humaninput import Typist, profiles

t = Typist(profile=profiles.load("touch_typist"), seed=42)
events = t.type("hello world")

for e in events:
    print(e.t_ms, e.action, e.key)
```

Render it somewhere instead of just reading timestamps:

```python
from humaninput.backends import terminal, svg

terminal.play(events)                 # replay to stdout with real timing
svg_markup = svg.render(events)       # animated SVG, no JS
```

## Mouse

```python
from humaninput.mouse.pointer import Pointer

p = Pointer(profile=profiles.load("touch_typist"), seed=1)
move = p.move(from_xy=(0, 0), to_xy=(800, 400), target_width=40)
click = p.click(800, 400)
```

## Touch

```python
from humaninput.touch import Touch

t = Touch(profile=profiles.load("mobile_thumbs"), seed=1)
tap = t.tap(120, 640)
drag = t.drag(from_xy=(50, 800), to_xy=(50, 200), target_width=60)  # e.g. a swipe
```

See **[Backends](backends.md)** for how to actually dispatch any of these streams — to a terminal, an SVG file, the real OS (`pynput`), or a live Playwright page (`browser`/`touch`).

## CLI

```bash
humaninput type "text to type"                          # replay to terminal
humaninput type -f script.txt --profile tired
humaninput type "text" --backend svg -o out.svg
humaninput mouse --from 100,100 --to 800,600 --backend json
humaninput profiles                                      # list available profiles/layouts
humaninput validate --profile touch_typist                # run stat checks, print report
```

Full flag reference: **[CLI reference](cli.md)**.
