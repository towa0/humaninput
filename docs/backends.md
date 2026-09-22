# Backends

Each backend is a consumer of an `EventStream` — the timing engine never performs I/O itself (see [Home → Core design decision](index.md#core-design-decision)). Every optional dependency is lazily imported inside the function that needs it, so `import humaninput` never requires any of them.

| backend | dependency | does |
|---|---|---|
| `terminal` | none | replays typing into stdout with real timing (the default) |
| `json` | none | dumps the raw event stream |
| `svg` | none | animated SVG with a blinking cursor, no JS |
| `css_keyframes` | none | a CSS `@keyframes` typing animation |
| `asciinema` | none | writes a `.cast` v2 file |
| `matplotlib` | `matplotlib` | plots trajectories and interval histograms |
| `pynput` | `pynput` | drives the **real** OS keyboard/mouse |
| `browser` | none (BYO Playwright `Page`) | raw CDP key/mouse dispatch into a live page |
| `touch` | none (BYO Playwright `Page`) | raw CDP touch dispatch into a live page |

## `terminal`

```python
from humaninput.backends import terminal

terminal.play(stream, speed=1.0, out=None, width=None)
```

Writes keydown characters at the timestamps in the stream, scaled by `1/speed`. Row-aware redraw via ANSI — once the buffer wraps onto multiple terminal rows, a naive clear-line-and-redraw only fixes the last row, so this repaints all wrapped rows. `width` defaults to the real terminal width.

## `json`

```python
from humaninput.backends import json as json_backend

json_backend.to_json(stream, indent=2) -> str
json_backend.write(stream, path_or_file, indent=2)
```

Dumps the raw event stream (`EventStream.to_dicts()`) — the format every other backend, and `humaninput fit`'s round-trip tests, treat as the canonical interchange shape.

## `svg`

```python
from humaninput.backends import svg

svg.render(stream, **kwargs) -> str
svg.write(stream, path, **kwargs)
```

Animated SVG with a blinking cursor and no JavaScript — safe to drop straight into a README or any Markdown renderer that allows inline SVG (this is what generates the animation at the top of the [README](https://github.com/towa0/humaninput)).

## `css_keyframes`

```python
from humaninput.backends import css_keyframes

css_keyframes.render(stream, **kwargs) -> str
```

A CSS `@keyframes` typing animation for embedding directly in a web page's stylesheet.

## `asciinema`

```python
from humaninput.backends import asciinema

asciinema.write(stream, path, **kwargs)
```

Writes an [asciinema](https://asciinema.org/) `.cast` v2 file — playable with the `asciinema` CLI or embeddable via asciinema-player.

## `matplotlib`

```python
from humaninput.backends import matplotlib as mpl_backend

mpl_backend.plot_trajectory(stream, show=True, ax=None)
mpl_backend.plot_interval_histogram(stream, profile=None, median_ms=None, show=True, ax=None)
```

Used for the validation figures in the README and for eyeballing a generated mouse trajectory or interval distribution during profile tuning.

## `pynput`

```python
from humaninput.backends import pynput as pynput_backend

pynput_backend.play_keys(stream)   # KeyEvent stream
pynput_backend.play_mouse(stream)  # MouseEvent stream
```

Drives the **real** OS keyboard/mouse. `pip install humaninput[pynput]`. Prints a warning on first use of either function per process. Implements a fail-safe modeled on pyautogui's: if the real cursor is found at a screen corner when a mouse event is about to be dispatched, playback aborts immediately (`RuntimeError`).

This is what `humaninput/tools/automate.py` and `shadow_writer.py` are built on — see [Tools](tools.md).

## `browser`

```python
from humaninput.backends import browser

browser.play_keys(stream, page)   # KeyEvent stream
browser.play_mouse(stream, page)  # MouseEvent stream
```

`page` is a live Playwright `Page` (sync API) that the caller already created — this module never imports `playwright` itself, it just calls `page.context.new_cdp_session(page)` and sends raw CDP commands (`Input.dispatchKeyEvent`, `Input.dispatchMouseEvent`). This is deliberate: Playwright's own `page.type()`/`page.click()` have their own internal pacing, which would throw away this library's timing model. Dispatching at the CDP layer preserves it.

`click`/`dblclick` marker events in a `MouseEvent` stream are skipped — the `down`/`up` pair already dispatched is what a real click is made of.

```python
from playwright.sync_api import sync_playwright
from humaninput import Typist, profiles
from humaninput.backends import browser

with sync_playwright() as p:
    page = p.chromium.launch().new_page()
    page.goto("https://example.com")
    stream = Typist(profile=profiles.load("touch_typist"), seed=1).type("hello")
    browser.play_keys(stream, page)
```

## `touch`

```python
from humaninput.backends import touch

touch.play_touch(stream, page)  # TouchEvent stream
```

Same no-import pattern as `browser`, dispatching `Input.dispatchTouchEvent`. `tap` marker events are skipped — `touchstart`/`touchend` are the real input. Pairs with `humaninput.touch.Touch` (`tap`, `drag`) and the `mobile_thumbs` profile's `[touch]` section — see [The model → Touch](model.md#touch).

```python
from humaninput.touch import Touch
from humaninput.backends import touch as touch_backend

t = Touch(profile=profiles.load("mobile_thumbs"), seed=1)
touch_backend.play_touch(t.tap(120, 640), page)
```
