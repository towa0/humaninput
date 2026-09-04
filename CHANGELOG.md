# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Arrow-key correction: a nearby typo can be fixed by navigating back to it
  (arrow-left, backspace/retype, arrow-right) instead of always backspacing
  through everything typed after it (`errors.arrow_correction_probability`,
  `errors.arrow_correction_max_tail`).
- Cascading retype errors: a correction's retype can itself come out wrong
  and get immediately fixed, bounded by `errors.max_cascade_depth`
  (`errors.retype_error_rate_multiplier`).
- Pace wander: overall typing speed now drifts up and down over time via a
  mean-reverting random walk (new `[pace]` profile section), instead of only
  per-keystroke noise around a flat average.
- Comma cognitive pause (`cognitive_pauses.comma_probability` and
  `comma_pause_ms_min`/`max`).
- New `humaninput/replay.py`: shared cursor-aware text-buffer simulation used
  by the `terminal`, `svg`, `css_keyframes`, and `asciinema` backends so
  arrow-key correction renders correctly (mid-line edits, not just
  append/backspace-at-end).

### Fixed

- `humaninput validate` on the `tired` profile: the isolated copies used for
  its digraph-ordering and KS checks didn't disable `fatigue`, so its
  monotonic interval drift broke the log-normal fit.

## [0.1.0] - 2026-08-22

### Added

- Timing engine: log-normal inter-key intervals, digraph-class multipliers
  from layout tables, independent key-hold sampling with rollover, burst and
  cognitive-pause modeling.
- Error injection and delayed-detection correction (substitution,
  transposition, insertion, omission).
- Mouse movement generator: Fitts's-law duration, minimum-jerk ballistic
  sub-movement plus corrective sub-movements, value-noise tremor.
- Profile fitting from recorded CSV (`humaninput fit`).
- Backends: `terminal`, `json`, `svg`, `css_keyframes`, `asciinema`,
  `matplotlib`, `pynput`.
- CLI: `type`, `mouse`, `fit`, `profiles`, `validate`.
- Shipped profiles: `touch_typist`, `hunt_and_peck`, `fast_coder`,
  `mobile_thumbs`, `tired`.
- Shipped layouts: `qwerty`, `dvorak`, `colemak`, `azerty`.
