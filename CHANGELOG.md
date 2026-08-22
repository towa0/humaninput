# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
