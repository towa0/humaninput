# The model

## Typing

### Inter-key intervals

Each inter-key interval is drawn from a **log-normal** distribution (`profile.interval`, `distribution = "lognormal"` — the only supported distribution right now, see [Profiles](profiles.md)):

```
interval ~ LogNormal(median = mu_ms * digraph_multiplier, sigma = interval.sigma)
```

Log-normal, not Gaussian: human inter-key intervals are right-skewed — most keystrokes land close to the mode, with an occasional long tail (a moment's hesitation, a harder reach). A Gaussian never produces that tail.

### Digraph classification

The median for a given transition is `interval.mu_ms` scaled by a **digraph-class multiplier** (`profile.digraph_multipliers`), derived from a keyboard [layout](layouts.md) table — which hand, which finger, same key vs. same finger vs. different finger produced the previous character vs. this one:

| class | typical relation to baseline | meaning |
|---|---|---|
| `same_key` | fastest (`0.60`) | repeating the same key |
| `alternating_hand` | fast (`0.85`) | left/right hand alternation |
| `same_hand_different_finger` | baseline (`1.0`) | same hand, different finger — the reference point every other multiplier is relative to |
| `same_finger_different_key` | slow (`1.60`) | same finger reaching to a different key |
| `to_punctuation` / `from_punctuation` | slower (`1.30`) | transition into/out of punctuation |
| `to_digit` | slowest (`2.0`) | digits break touch-typing muscle memory hardest |

Classification (`Layout.classify_digraph`, see [Layouts](layouts.md)) checks digit → punctuation → physical key relationship, in that priority order.

### Key hold duration and rollover

Key **hold** (down-to-up) duration is sampled independently of the inter-key interval, from `profile.hold` (log-normal, `mu_ms`/`sigma`). Because it's independent, fast profiles legitimately produce overlapping down/up pairs — **rollover**, one of the strongest tells between real and simulated typing. `profile.rollover.probability` is the chance a given keystroke's release is forced to wait until after the *next* key's press (plus `overlap_ms_mu` of overlap), rather than releasing on its own schedule.

### Bursts and cognitive pauses

Typing comes in **bursts**: a geometrically-distributed run length (`profile.burst.mean_length`) of keystrokes at normal pace, followed by a micro-pause (`burst.pause_ms_mu`/`sigma`) before the next burst starts. This is layered under everything else — it doesn't replace the per-keystroke interval, it adds an extra pause when a burst ends.

Separately, **cognitive pauses** (`profile.cognitive_pauses`) fire before: a rare word (looked up against the top-5000 common-word list — see [Word list](https://github.com/towa0/humaninput#word-list)), a digit run, an opening bracket/quote, or a sentence start — each an independent trigger probability, combined as `1 - ∏(1 - p_i)` so multiple simultaneous triggers (e.g. a rare word that's also a sentence start) don't just stack additively past 1. A separate, shorter pause can fire after a comma (`comma_probability`, `comma_pause_ms_min`/`max`).

### Pace wander

On top of per-keystroke noise, overall pace **wanders**: `profile.pace` runs a mean-reverting random walk in log-space (an Ornstein-Uhlenbeck process — `state += -reversion_rate * state + volatility * N(0,1)`, then `multiplier = clamp(exp(state), min_multiplier, max_multiplier)`) that multiplies every interval. A 130-WPM profile doesn't hold a flat 130 — it drifts faster and slower over tens of characters and reverts, the way a real typing session speeds up and slows down rather than metronoming.

### Fatigue

`profile.fatigue`, when `enabled`, linearly increases the interval multiplier by `interval_drift_per_char` for every character typed so far in the stream — a session-long slowdown, distinct from pace wander's short-timescale ups and downs.

## Errors

Four error kinds, each firing at an independent, profile-configured rate (`profile.errors`): **substitution** (weighted toward physically adjacent keys via `Layout.neighbors`), **transposition**, **insertion**, **omission**.

The important part isn't the error itself — it's that **detection is delayed**, matching how people actually notice typos: `detection_delay_chars` (a `[min, max]` range of characters typed before noticing) and `detection_delay_word_probability` (a chance detection waits until the end of the current word instead). Once noticed, there's a pause (`notice_pause_ms_min`/`max`) and a correction.

### Correction strategies

`correction_strategy` (`"immediate"`, `"word"`, or `"ignore"`) controls when a correction is attempted at all; `uncorrected_rate` gives each detected error an independent chance of being left in the final text anyway (nobody catches every typo).

The retype itself isn't always a blind backspace-through-everything:

- With `arrow_correction_probability`, a correction close behind the cursor (within `arrow_correction_max_tail` characters) is fixed **in place** instead: arrow-left back to it, backspace/retype just that span, arrow-right back out — leaving correctly-typed characters after it untouched. This only happens when nothing else in that stretch still needs fixing; otherwise it falls back to backspace-and-retype, which repairs the whole span at once.
- The retype isn't guaranteed correct either: `retype_error_rate_multiplier` gives each retyped character a reduced chance of *also* coming out wrong — caught immediately and fixed with one more backspace. This can cascade (a fix that itself needs fixing), capped by `max_cascade_depth`.
- Backspace/arrow-key navigation events are timed like any other keystroke, but at `backspace_speed_multiplier` × the normal rate (faster — corrections are typically hammered out quicker than composition).

## Mouse movement

Movement duration comes from **Fitts's law**:

```
MT = a + b · log2(2D / W)
```

(Fitts, 1954) — not a fixed or distance-linear duration. `a`/`b` (`profile.mouse.fitts_a_ms`/`fitts_b_ms`) are empirical, per-person/device constants exposed as profile parameters rather than hardcoded, since they vary by input device and individual.

The trajectory itself is not one smooth Bézier curve. Real pointing is:

1. A **ballistic sub-movement** covering `ballistic_fraction_min`–`max` of the distance, following a **minimum-jerk** velocity profile (Flash & Hogan, 1985) — the unique smoothest rest-to-rest trajectory, `s(u) = 10u³ − 15u⁴ + 6u⁵` for `u = t/T ∈ [0,1]`, whose velocity `ds/du` is a single symmetric bell curve.
2. Zero to a few (Poisson-distributed, scaling with the Fitts index of difficulty via `correction_base_count`/`correction_count_per_id_bit`) smaller **corrective sub-movements**, each also minimum-jerk, closing the remaining error.
3. An occasional **overshoot** (`overshoot_probability`, `overshoot_fraction`) past the target before the first correction pulls back.
4. A low-amplitude **tremor** (`tremor_amplitude_px`, `tremor_frequency_hz`) layered on the finished path — correlated value noise (smooth, lattice-interpolated), not independent per-sample jitter, which is what reads as a hand instead of sensor static.

`click`/`dblclick`/`drag`/`scroll` each build on the same primitives — see `humaninput/mouse/pointer.py`.

## Touch

`humaninput.touch.Touch` (`tap`, `drag`) models **direct pointing** — a finger targeting glass — as distinct from the mouse's **indirect pointing** through a cursor. It's a genuinely different physical situation, so it's a separate config section (`profile.touch`) and a separate event type (`TouchEvent`: `touchstart`/`touchmove`/`touchend`/`tap`, no persistent cursor/hover state or button, unlike `MouseEvent`), even though the underlying path synthesis reuses the same minimum-jerk `generate_trajectory` — the biomechanical model isn't specific to one effector, only the *parameters* differ:

- **Far fewer in-flight corrections.** A finger commits to its destination directly; there's no continuous visual-feedback loop steering an indirect cursor the way there is with a mouse. `touch.correction_base_count`/`correction_count_per_id_bit` default well below the mouse equivalents.
- **No tremor by default** (`tremor_amplitude_px = 0.0`). Touchscreen digitizers debounce/smooth raw contact samples; the mouse's sensor-level tremor has no real analog at typical touch sample rates.
- **Lower sample rate** (`sample_rate_hz = 60.0` vs. the mouse's `120.0`), matching typical touchscreen reporting.

Pairs with the `mobile_thumbs` profile's `[touch]` section, which adds a bit of finger-pad wobble (`tremor_amplitude_px = 0.8`) back in for a small-screen thumb-typing scenario. See [Profiles](profiles.md#touch) for the full field list and [Backends](backends.md#touch) for dispatching a `TouchEvent` stream into a live page.

## References

- Fitts, P. M. (1954). *The information capacity of the human motor system in controlling the amplitude of movement.* Journal of Experimental Psychology, 47(6), 381–391.
- Flash, T., & Hogan, N. (1985). *The coordination of arm movements: an experimentally confirmed mathematical model.* Journal of Neuroscience, 5(7), 1688–1703.
- Dhakal, V., Feit, A. M., Kristensson, P. O., & Oulasvirta, A. (2018). *Observations on Typing from 136 Million Keystrokes.* CHI 2018 — digraph-level keystroke latency effects.
