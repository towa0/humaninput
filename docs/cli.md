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
