# Profiles

A profile is plain-data TOML — no source reading required to write one. Shipped in `humaninput/profiles/`: `touch_typist`, `hunt_and_peck`, `fast_coder`, `mobile_thumbs`, `tired`.

```bash
humaninput profiles                              # list available profiles/layouts
humaninput fit recorded.csv -o my_profile.toml   # calibrate against real typing (csv: timestamp_ms,key,action)
```

Every field below has a default, so a profile only needs to override what it cares about. "Validated" means `humaninput.profile._validate` raises `ValueError` on load if the constraint is violated; "not validated" fields are trusted as-is — get them wrong and you'll see it in the output, not in a load-time error.

## Top level

| field | type | default | validated |
|---|---|---|---|
| `name` | str | `"default"` | no |
| `wpm_target` | float | `70.0` | **yes** — must be `> 0` |
| `layout` | str | `"qwerty"` | indirectly — resolved via [`load_layout`](layouts.md), raises `FileNotFoundError` if missing |

## `[interval]`

Inter-key interval distribution. See [The model → Inter-key intervals](model.md#inter-key-intervals).

| field | type | default | validated |
|---|---|---|---|
| `distribution` | str | `"lognormal"` | **yes** — must be exactly `"lognormal"` (only distribution currently supported) |
| `mu_ms` | float | `145.0` | no |
| `sigma` | float | `0.42` | no |

## `[digraph_multipliers]`

Multipliers on `interval.mu_ms`, keyed by transition class (see [The model → Digraph classification](model.md#digraph-classification)). None are validated; all are relative to `same_hand_different_finger = 1.0`.

| field | default |
|---|---|
| `same_key` | `0.60` |
| `alternating_hand` | `0.85` |
| `same_hand_different_finger` | `1.0` |
| `same_finger_different_key` | `1.60` |
| `to_punctuation` | `1.30` |
| `from_punctuation` | `1.30` |
| `to_digit` | `2.0` |

## `[hold]`

Key hold (down-to-up) duration, independent of inter-key interval.

| field | type | default | validated |
|---|---|---|---|
| `mu_ms` | float | `88.0` | no |
| `sigma` | float | `0.30` | no |

## `[rollover]`

| field | type | default | validated |
|---|---|---|---|
| `probability` | float | `0.35` | no — keep in `[0, 1]` |
| `overlap_ms_mu` | float | `22.0` | no |

## `[burst]`

| field | type | default | validated |
|---|---|---|---|
| `mean_length` | float | `6.5` | no — internally clamped to `>= 1.0` before use as the geometric-distribution parameter |
| `pause_ms_mu` | float | `220.0` | no |
| `pause_ms_sigma` | float | `0.5` | no |

## `[cognitive_pauses]`

| field | type | default | validated |
|---|---|---|---|
| `rare_word_probability` | float | `0.35` | no — keep in `[0, 1]` |
| `digit_probability` | float | `0.55` | no — keep in `[0, 1]` |
| `bracket_probability` | float | `0.30` | no — keep in `[0, 1]` |
| `sentence_start_probability` | float | `0.45` | no — keep in `[0, 1]` |
| `pause_ms_min` | float | `400.0` | no |
| `pause_ms_max` | float | `2000.0` | no |
| `comma_probability` | float | `0.20` | no — keep in `[0, 1]` |
| `comma_pause_ms_min` | float | `120.0` | no |
| `comma_pause_ms_max` | float | `450.0` | no |

## `[fatigue]`

| field | type | default | validated |
|---|---|---|---|
| `enabled` | bool | `false` | no |
| `interval_drift_per_char` | float | `0.0004` | no |
| `error_rate_drift_per_char` | float | `0.000015` | no |

## `[pace]`

See [The model → Pace wander](model.md#pace-wander).

| field | type | default | validated |
|---|---|---|---|
| `enabled` | bool | `true` | no |
| `reversion_rate` | float | `0.02` | no |
| `volatility` | float | `0.045` | no |
| `min_multiplier` | float | `0.8` | **yes** — must be `> 0` |
| `max_multiplier` | float | `1.3` | **yes** — must be `>= min_multiplier` |

## `[errors]`

See [The model → Errors](model.md#errors).

| field | type | default | validated |
|---|---|---|---|
| `substitution_rate` | float | `0.008` | **yes** — `[0, 1]` |
| `transposition_rate` | float | `0.004` | **yes** — `[0, 1]` |
| `insertion_rate` | float | `0.002` | **yes** — `[0, 1]` |
| `omission_rate` | float | `0.003` | **yes** — `[0, 1]` |
| `detection_delay_chars` | `[int, int]` | `[1, 3]` | **yes** — `min >= 0` and `max >= min` |
| `detection_delay_word_probability` | float | `0.08` | no — keep in `[0, 1]` |
| `correction_strategy` | str | `"word"` | **yes** — one of `"immediate"`, `"word"`, `"ignore"` |
| `uncorrected_rate` | float | `0.05` | **yes** — `[0, 1]` |
| `backspace_speed_multiplier` | float | `0.7` | no |
| `notice_pause_ms_min` | float | `150.0` | no |
| `notice_pause_ms_max` | float | `500.0` | no |
| `arrow_correction_probability` | float | `0.35` | **yes** — `[0, 1]` |
| `arrow_correction_max_tail` | int | `10` | **yes** — must be `>= 0` |
| `retype_error_rate_multiplier` | float | `0.4` | **yes** — `[0, 1]` |
| `max_cascade_depth` | int | `2` | **yes** — must be `>= 0` |

## `[mouse]`

Indirect (cursor) pointing physics. See [The model → Mouse movement](model.md#mouse-movement).

| field | type | default | validated |
|---|---|---|---|
| `fitts_a_ms` | float | `50.0` | no |
| `fitts_b_ms` | float | `150.0` | no |
| `sample_rate_hz` | float | `120.0` | no |
| `ballistic_fraction_min` | float | `0.85` | no |
| `ballistic_fraction_max` | float | `0.95` | no |
| `correction_base_count` | float | `0.5` | no |
| `correction_count_per_id_bit` | float | `0.35` | no |
| `overshoot_probability` | float | `0.25` | no — keep in `[0, 1]` |
| `overshoot_fraction` | float | `0.06` | no |
| `tremor_amplitude_px` | float | `0.6` | no |
| `tremor_frequency_hz` | float | `8.0` | no |
| `click_hold_ms_mu` | float | `90.0` | no |
| `click_hold_ms_sigma` | float | `0.25` | no |
| `dblclick_interval_ms_mu` | float | `180.0` | no |
| `dblclick_interval_ms_sigma` | float | `0.2` | no |
| `drag_speed_multiplier` | float | `0.6` | no |
| `scroll_detent_ms_mu` | float | `45.0` | no |
| `scroll_detent_ms_sigma` | float | `0.3` | no |

## `[touch]`

Direct (finger-on-glass) pointing physics — a distinct config section from `[mouse]`, not a relabeling of it. See [The model → Touch](model.md#touch).

| field | type | default | validated |
|---|---|---|---|
| `fitts_a_ms` | float | `30.0` | no |
| `fitts_b_ms` | float | `120.0` | no |
| `sample_rate_hz` | float | `60.0` | no |
| `ballistic_fraction_min` | float | `0.94` | no |
| `ballistic_fraction_max` | float | `1.0` | no |
| `correction_base_count` | float | `0.15` | no |
| `correction_count_per_id_bit` | float | `0.08` | no |
| `overshoot_probability` | float | `0.10` | no — keep in `[0, 1]` |
| `overshoot_fraction` | float | `0.04` | no |
| `tremor_amplitude_px` | float | `0.0` | no |
| `tremor_frequency_hz` | float | `6.0` | no |
| `tap_hold_ms_mu` | float | `80.0` | no |
| `tap_hold_ms_sigma` | float | `0.30` | no |
| `drag_speed_multiplier` | float | `0.8` | no |

## Shipped profiles at a glance

| profile | notes |
|---|---|
| `touch_typist` | 75 WPM, low error rate, strong rollover |
| `hunt_and_peck` | 30 WPM, high variance, long pauses on digits/symbols, minimal rollover |
| `fast_coder` | 100 WPM on alphanumerics, disproportionately slow on symbols/brackets, high correction rate |
| `mobile_thumbs` | high variance, high adjacent-key substitution rate, word-level autocorrect-style corrections, tuned `[mouse]`/`[touch]` sections for a small touchscreen |
| `tired` | `touch_typist` with fatigue drift and elevated error rate |

Unknown keys in any section raise `ValueError` at load time (`_build_section` checks against the dataclass's known field names) — a typo in a profile TOML fails loudly instead of being silently ignored.
