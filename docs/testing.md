# Testing with Playwright

`pip install humaninput-testing[playwright]` adds Playwright and pytest. Neither is imported by `import humaninput`.

## `type_into`

```python
from humaninput.playwright import type_into

stream = type_into(locator, "Amsterdam", profile="hunt_and_peck", seed=13)
```

| argument | default | meaning |
|---|---|---|
| `locator` | required | a Playwright `Locator` (sync API) |
| `text` | required | what the simulated person means to type |
| `profile` | `touch_typist` | profile name, path to a profile TOML, or a `Profile` |
| `seed` | `None` | same seed, same keystrokes and timing; `None` is different each call |
| `errors` | `True` | simulate typos and their corrections |
| `layout` | from profile | keyboard layout override |
| `virtual_time` | `False` | advance the page clock instead of sleeping (see below) |

It clicks the locator, generates the stream with `Typist`, and plays it through the [`browser` backend](backends.md#browser). It returns the stream so a test can log it.

It clicks rather than calling `focus()`, because people click a field before typing and apps often react to that click. Clicking puts the caret where the click lands, so clear a field that already has text first.

With `errors=True` the field can end up with an uncorrected typo, the way a person's would. Assert against the field's actual value, not against `text`.

## Virtual time

By default `type_into` sleeps between key events, so a 5-second stream takes 5 seconds. Timers in the page then run on the real clock, and a busy machine can shift them by a few milliseconds.

With `virtual_time=True` it uses Playwright's [clock](https://playwright.dev/python/docs/clock) instead. Install and pause the clock before loading the page:

```python
page.clock.install(time=0)
page.clock.pause_at(1)
page.goto(url)

type_into(box, "Amsterdam", seed=7, virtual_time=True)
page.clock.run_for(1500)   # let debounces and timeouts finish
```

It then advances the page clock by each gap between events and never sleeps. `setTimeout`, `Date` and `performance.now` in the page see exactly the stream's timing, and the stream plays in a fraction of its real duration. The clock only advances in whole milliseconds.

Anything else in the test that waits in real time won't move a paused clock. For example, `press_sequentially(text, delay=...)` waits in real time, so a debounce never fires between its keys. Advance the clock yourself with `page.clock.run_for(ms)`.

## Seed sweeps

```python
import pytest
from humaninput.playwright import type_into
from humaninput.testing import describe, seeds

@pytest.mark.parametrize("seed", seeds(20))
def test_search(page, seed):
    box = page.get_by_role("searchbox")
    stream = type_into(box, "Amsterdam", profile="hunt_and_peck", seed=seed)
    assert results_match(page, box.input_value()), describe(stream)
```

`seeds(n, start=0)` returns `pytest.param`s with ids like `seed=13`, so a failure reads `test_search[seed=13]`. With pytest-playwright's `page` fixture it reads `test_search[chromium-seed=13]`. Run that id again to replay the exact keystrokes and timing.

`describe(stream)` is one line for an assertion message:

```
seed=13 hunt_and_peck: 4.35 s, 15 keystrokes, 1 correction, longest pause 1002 ms
```
