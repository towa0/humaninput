# Autocomplete race

A city search box with a bug planted on purpose. The bug class is common in real apps: a slow response for an old query arrives after the response for the current one and overwrites it. You type "Amsterdam" and the page shows results for "Amsterd".

## The app

`app.html` is one static page with no build step and no network requests. The component lives in `autocomplete.js`, which the docs demo also uses.

- Input is debounced by 300 ms. A search is sent only after 300 ms without typing.
- `fakeSearch(query)` simulates a server. Its latency is a fixed function of the query string (a hash mapped to 100–1100 ms). Random latency would make failures impossible to replay. Real networks do vary, which is one more reason these bugs reach production.
- **The bug:** the results area shows whichever response arrives last. Nothing checks whether it is still the latest query.
- **The fix:** open `app.html?fixed=1`. Each request gets an id, and a response is ignored unless its id is the latest one.

With these latencies, "Amsterd" takes 1049 ms and "Amsterdam" takes 183 ms. A search for "Amsterd" only goes out if the typist pauses at least 300 ms after the "d". It then loses the race only if the search for "Amsterdam" goes out less than 866 ms later. So the bug needs a pause in one place and quick typing just after it.

## The tests

Each test types into the box, waits 1.5 s, then checks that "Results for:" matches the input's current value. It compares with the box, not the intended text, because a typist can leave a typo uncorrected.

| test | app | how it types | result |
|---|---|---|---|
| `test_fill` | buggy | `locator.fill("Amsterdam")` | passes: one input event, one request |
| `test_fixed_delay` | buggy | `press_sequentially(..., delay=100)` | passes: no pause reaches 300 ms, so only one request goes out |
| `test_fixed_delay_slow` | buggy | `press_sequentially(..., delay=400)` | **fails** (marked xfail, strict) |
| `test_human[seed=0..19]` | buggy | `type_into(..., profile="hunt_and_peck", seed=seed)` | **5 of 20 fail**: seeds 1, 7, 8, 10, 12 (marked xfail) |
| `test_human_fixed[seed=0..19]` | `?fixed=1` | same 20 seeds | all pass |

A fixed delay can catch this if you guess the right value. With these latencies, 300–400 ms fails and 50–250 or 450–600 ms passes. With a different query or different latencies, the values that fail would be different. Seeds spread the timing across many runs, so you don't have to guess, and a failing seed replays exactly.

Every failing seed shows "Amsterd". In each one the typist paused long enough after "d" for that search to go out, then typed "am" fast enough for "Amsterdam" to be sent within 866 ms. The other seeds either typed straight through "d" without a 300 ms pause, or paused again before the last letters.

## Running

From the repo root, with `pip install -e ".[playwright]"` and `playwright install chromium`:

```bash
pytest examples/autocomplete-race               # buggy-app failures show as xfail
pytest examples/autocomplete-race --runxfail    # show them as real failures
pytest "examples/autocomplete-race/test_autocomplete.py::test_human[seed=7]" --runxfail
```

The last command replays one failing seed: same keystrokes, same timing, same stale result.

The buggy-app tests are marked `xfail` so the repo's own runs stay green. Without Playwright or Chromium, the tests are skipped.

The whole folder takes about 4 min 40 s on my machine, because each test types in real time. If you have pytest-xdist, `pytest -n auto examples/autocomplete-race` runs the tests in parallel. On my machine that took 42 s and the same seeds failed. This repo doesn't depend on xdist.

## Fragile spots

Some seeds are close to the threshold. Seed 12 fails by 38 ms, seed 2 passes by 13 ms and seed 17 passes by 38 ms. A heavily loaded machine adds jitter to the key timings and browser timers, and could flip those seeds. The other seeds have at least 50 ms of margin.
