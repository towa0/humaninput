# Autocomplete race

A city search box with a bug planted on purpose. The bug class is common in real apps: a slow response for an old query arrives after the response for the current one and overwrites it. You type "Amsterdam" and the page shows results for "Amsterd".

## The app

`app.html` is one static page with no build step and no network requests. The component lives in `autocomplete.js`. The docs demo uses a byte-identical copy of it, and a test checks that the two copies match.

- Input is debounced by 300 ms. A search is sent only after 300 ms without typing.
- `fakeSearch(query)` simulates a server. Its latency is a fixed function of the query string (a hash mapped to 100–1100 ms). Random latency would make failures impossible to replay. Real networks do vary, which is one more reason these bugs reach production.
- **The bug:** the results area shows whichever response arrives last. Nothing checks whether it is still the latest query.
- **The fix:** open `app.html?fixed=1`. Each request gets an id, and a response is ignored unless its id is the latest one.

With these latencies, "Amsterd" takes 1049 ms and "Amsterdam" takes 183 ms. A search for "Amsterd" only goes out if the typist pauses at least 300 ms after the "d". It then loses the race only if the search for "Amsterdam" goes out less than 866 ms later. So the bug needs a pause in one place and quick typing just after it.

I chose the simulated latencies so this race can happen. My first range, 80–900 ms, never triggered it: no early query was slow enough to lose to the final one. With the values above, 5 of 20 seeds hit it. Other latencies, another query or another profile would give a different number of failing seeds, maybe none.

## The tests

Each test types into the box, lets 1.5 s pass, then checks that "Results for:" matches the input's current value. It compares with the box, not the intended text, because a typist can leave a typo uncorrected.

| test | app | how it types | result |
|---|---|---|---|
| `test_fill` | buggy | `locator.fill("Amsterdam")` | passes: one input event, one request |
| `test_fixed_delay` | buggy | one key every 100 ms | passes: no pause reaches 300 ms, so only one request goes out |
| `test_fixed_delay_slow` | buggy | one key every 400 ms | **fails** (marked xfail, strict) |
| `test_human[seed=0..19]` | buggy | `type_into(..., profile="hunt_and_peck", seed=seed)` | **5 of 20 fail**: seeds 1, 7, 8, 10, 12 (marked xfail) |
| `test_human_fixed[seed=0..19]` | `?fixed=1` | same 20 seeds | all pass |

A fixed delay can catch this if you guess the right value. I measured it in the browser. Delays from 300 to 432 ms fail. Delays of 290 ms and below pass, and so do 433 ms and above. The window follows from the latencies: a 300 ms gap lets "Amsterd" go out, and two more gaps must add up to less than 866 ms. With another query or other latencies, the window would be somewhere else. Seeds spread the timing across many runs, so you don't have to guess, and a failing seed replays exactly.

Every failing seed shows "Amsterd". In each one the typist paused long enough after "d" for that search to go out, then typed "am" fast enough for "Amsterdam" to be sent within 866 ms. The other seeds either typed straight through "d" without a 300 ms pause, or paused again before the last letters.

## Virtual time

The tests install Playwright's fake clock and pause it before loading the page:

```python
page.clock.install(time=0)
page.clock.pause_at(1)
page.goto(APP)
type_into(box, "Amsterdam", profile="hunt_and_peck", seed=7, virtual_time=True)
page.clock.run_for(1500)
```

With `virtual_time=True`, `type_into` doesn't sleep. It advances the page clock by each gap between key events, so the page's debounce and latency timers fire at exactly the typed times. A slow or busy machine can't shift them.

The fixed-delay tests press one key at a time and advance the clock between presses. `press_sequentially(text, delay=...)` would wait in real time, and a paused page clock ignores real time.

## Running

From the repo root, with `pip install -e ".[playwright]"` and `playwright install chromium`:

```bash
pytest examples/autocomplete-race               # buggy-app failures show as xfail
pytest examples/autocomplete-race --runxfail    # show them as real failures
pytest "examples/autocomplete-race/test_autocomplete.py::test_human[seed=7]" --runxfail
```

The last command replays one failing seed: same keystrokes, same timing, same stale result.

The buggy-app tests are marked `xfail` so the repo's own runs stay green. Without Playwright or Chromium, the tests are skipped. CI runs this folder in a separate `browser` job, along with the other tests marked `browser`.

The whole folder (43 tests) takes about 17 s on my machine. Before virtual time it took 4 min 40 s, because every test typed in real time. If you have pytest-xdist, `pytest -n auto examples/autocomplete-race` runs the tests in parallel. This repo doesn't depend on xdist.

## How close the seeds are

Some seeds are close to the threshold. Seed 12 fails by 38 ms, seed 2 passes by 13 ms, and seed 17 passes by 38 ms. In real time, a heavily loaded machine could flip them. In virtual time they can't: I ran the folder 5 times and got the same failures each time. The gaps between search events in the page were identical to the millisecond.
