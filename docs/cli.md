# CLI reference

```bash
humaninput <command> [options]
```

## `type`

Generate typing events and replay/export them.

```bash
humaninput type "text to type"
humaninput type -f script.txt --profile tired
humaninput type "text" --backend svg -o out.svg
humaninput type "text" --backend json -o events.json --seed 42
```

| flag | default | meaning |
|---|---|---|
| `text` (positional) | — | text to type; reads stdin if omitted and `-f` not given |
| `-f`, `--file` | — | read text to type from a file |
| `--profile` | `touch_typist` | profile name or path |
| `--layout` | from profile | keyboard layout override |
| `--seed` | none | random seed for reproducible output |
| `--speed` | `1.0` | terminal backend playback speed multiplier |
| `--no-errors` | off | disable typo/correction simulation |
| `--backend` | `terminal` | one of `terminal`, `json`, `svg`, `css`, `asciinema`, `pynput` |
| `-o`, `--output` | stdout | write to file instead of stdout (svg/json/css/asciinema) |

## `mouse`

Generate mouse-movement events and export them.

```bash
humaninput mouse --from 100,100 --to 800,600 --target-width 40 --backend json
```

| flag | default | meaning |
|---|---|---|
| `--from` | required | start position, e.g. `100,100` |
| `--to` | required | end position, e.g. `800,600` |
| `--target-width` | `40.0` | Fitts's law target width in px |
| `--action` | `move` | one of `move`, `drag`, `click`, `dblclick` |
| `--profile` | `touch_typist` | profile name or path |
| `--seed` | none | random seed |
| `--backend` | `json` | one of `json`, `matplotlib`, `pynput` |
| `-o`, `--output` | stdout | write to file |

## `fit`

Fit a profile from a CSV of recorded keystroke timings.

```bash
humaninput fit recorded.csv -o my_profile.toml
```

| flag | default | meaning |
|---|---|---|
| `csv` (positional) | required | CSV with columns `timestamp_ms,key,action` |
| `-o`, `--output` | stdout | write fitted profile TOML to this path |
| `--name` | `fitted` | name for the fitted profile |
| `--layout` | `qwerty` | layout to classify digraphs against |

## `write-on-hotkey`

Listen for a global hotkey and type a text file's contents wherever OS focus is. Wraps `humaninput/tools/shadow_writer.py` — see [Tools](tools.md). Requires `pip install humaninput[pynput]`.

```bash
humaninput write-on-hotkey snippet.txt --hotkey "<ctrl>+<alt>+h"
```

| flag | default | meaning |
|---|---|---|
| `file` (positional) | required | text file to type; re-read on every trigger |
| `--hotkey` | `<ctrl>+<alt>+h` | global hotkey that starts typing |
| `--cancel-hotkey` | `<ctrl>+<alt>+x` | global hotkey that aborts in-progress typing |
| `--quit-hotkey` | `<ctrl>+<alt>+q` | global hotkey that stops the listener |
| `--profile` | `touch_typist` | profile name or path |
| `--layout` | none | layout override |
| `--seed` | none | random seed |
| `--delay` | `2.5` | seconds to wait after the hotkey before typing starts |
| `--no-errors` | off | disable typo/correction simulation |

## `click-type`

Move the real mouse to a point, click it, then type text there. Wraps `humaninput/tools/automate.py`'s `click_and_type` — see [Tools](tools.md). Requires `pip install humaninput[pynput]`.

```bash
humaninput click-type --to 500,300 "hello"
```

| flag | default | meaning |
|---|---|---|
| `--to` | required | target position to click, e.g. `500,300` |
| `--from` | current cursor position | start position |
| `text` (positional) | — | text to type; reads `-f`/`--file` if omitted |
| `-f`, `--file` | — | read text to type from a file |
| `--profile` | `touch_typist` | profile name or path |
| `--layout` | none | layout override |
| `--seed` | none | random seed |
| `--delay` | `3.0` | seconds to wait before acting, to switch to the target window |
| `--no-errors` | off | disable typo/correction simulation |

## `profiles`

List available profiles and layouts. No flags.

```bash
humaninput profiles
```

## `validate`

Run statistical validation checks against a profile: measured WPM vs. target, digraph-ordering sanity, seeded reproducibility, and (if `scipy` is installed) a Kolmogorov–Smirnov test against the configured log-normal interval distribution. Exit code `1` if any check fails.

```bash
humaninput validate --profile touch_typist
```

| flag | default | meaning |
|---|---|---|
| `--profile` | `touch_typist` | profile name or path |
