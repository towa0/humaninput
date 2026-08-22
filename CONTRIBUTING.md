# Contributing

## Setup

```bash
pip install -e ".[dev]"
```

## Tests

```bash
pytest
```

Tests include statistical checks (Kolmogorov-Smirnov, Fitts's law linear fit,
reproducibility with fixed seeds) — if a change shifts the underlying
distributions, expect some of these to need re-tuning, not just a code fix.

## Lint

```bash
ruff check .
```

## Adding a profile

Profiles are plain TOML under `humaninput/profiles/`, not code. Copy the
closest existing profile, adjust the fields, and validate it:

```bash
humaninput validate --profile your_profile
```

## Adding a layout

Layouts are plain TOML under `humaninput/layouts/`, generated with
`scripts/gen_layouts.py` from a hand-written key-position table. Add your
layout there rather than hand-editing the generated TOML.

## Adding a backend

A backend is a module under `humaninput/backends/` that consumes an
`EventStream` and does something with it. Optional dependencies must be
imported lazily inside the function that needs them — `import humaninput`
must never require them.

## Pull requests

Keep PRs focused on one change. Run `pytest` and `ruff check .` before
opening one.
