"""Profile loading: plain-data TOML files that parameterize the typing and
mouse models. A profile is the only thing a user needs to write to change
behavior — no source reading required.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field, fields

from humaninput import _toml

_PROFILES_DIR = pathlib.Path(__file__).parent / "profiles"


@dataclass
class IntervalConfig:
    distribution: str = "lognormal"
    mu_ms: float = 145.0
    sigma: float = 0.42


@dataclass
class DigraphMultipliers:
    same_key: float = 0.60
    alternating_hand: float = 0.85
    same_hand_different_finger: float = 1.0
    same_finger_different_key: float = 1.60
    to_punctuation: float = 1.30
    from_punctuation: float = 1.30
    to_digit: float = 2.0


@dataclass
class HoldConfig:
    mu_ms: float = 88.0
    sigma: float = 0.30


@dataclass
class RolloverConfig:
    probability: float = 0.35
    overlap_ms_mu: float = 22.0


@dataclass
class BurstConfig:
    mean_length: float = 6.5
    pause_ms_mu: float = 220.0
    pause_ms_sigma: float = 0.5


@dataclass
class CognitivePauseConfig:
    rare_word_probability: float = 0.35
    digit_probability: float = 0.55
    bracket_probability: float = 0.30
    sentence_start_probability: float = 0.45
    pause_ms_min: float = 400.0
    pause_ms_max: float = 2000.0
    comma_probability: float = 0.20
    comma_pause_ms_min: float = 120.0
    comma_pause_ms_max: float = 450.0


@dataclass
class FatigueConfig:
    enabled: bool = False
    interval_drift_per_char: float = 0.0004
    error_rate_drift_per_char: float = 0.000015


@dataclass
class PaceConfig:
    """Slow mean-reverting drift on top of the per-keystroke interval
    noise, so overall speed wanders (ups and downs over tens of
    characters) instead of holding a flat average forever. An
    Ornstein-Uhlenbeck process in log-space: `reversion_rate` pulls it
    back toward baseline, `volatility` is the size of each random nudge.
    """

    enabled: bool = True
    reversion_rate: float = 0.02
    volatility: float = 0.045
    min_multiplier: float = 0.8
    max_multiplier: float = 1.3


@dataclass
class ErrorConfig:
    substitution_rate: float = 0.008
    transposition_rate: float = 0.004
    insertion_rate: float = 0.002
    omission_rate: float = 0.003
    detection_delay_chars: tuple[int, int] = (1, 3)
    detection_delay_word_probability: float = 0.08
    correction_strategy: str = "word"
    uncorrected_rate: float = 0.05
    backspace_speed_multiplier: float = 0.7
    notice_pause_ms_min: float = 150.0
    notice_pause_ms_max: float = 500.0
    arrow_correction_probability: float = 0.35
    arrow_correction_max_tail: int = 10
    retype_error_rate_multiplier: float = 0.4
    max_cascade_depth: int = 2


@dataclass
class MouseConfig:
    fitts_a_ms: float = 50.0
    fitts_b_ms: float = 150.0
    sample_rate_hz: float = 120.0
    ballistic_fraction_min: float = 0.85
    ballistic_fraction_max: float = 0.95
    correction_base_count: float = 0.5
    correction_count_per_id_bit: float = 0.35
    overshoot_probability: float = 0.25
    overshoot_fraction: float = 0.06
    tremor_amplitude_px: float = 0.6
    tremor_frequency_hz: float = 8.0
    click_hold_ms_mu: float = 90.0
    click_hold_ms_sigma: float = 0.25
    dblclick_interval_ms_mu: float = 180.0
    dblclick_interval_ms_sigma: float = 0.2
    drag_speed_multiplier: float = 0.6
    scroll_detent_ms_mu: float = 45.0
    scroll_detent_ms_sigma: float = 0.3


@dataclass
class Profile:
    name: str = "default"
    wpm_target: float = 70.0
    layout: str = "qwerty"
    interval: IntervalConfig = field(default_factory=IntervalConfig)
    digraph_multipliers: DigraphMultipliers = field(default_factory=DigraphMultipliers)
    hold: HoldConfig = field(default_factory=HoldConfig)
    rollover: RolloverConfig = field(default_factory=RolloverConfig)
    burst: BurstConfig = field(default_factory=BurstConfig)
    cognitive_pauses: CognitivePauseConfig = field(default_factory=CognitivePauseConfig)
    fatigue: FatigueConfig = field(default_factory=FatigueConfig)
    pace: PaceConfig = field(default_factory=PaceConfig)
    errors: ErrorConfig = field(default_factory=ErrorConfig)
    mouse: MouseConfig = field(default_factory=MouseConfig)


_SECTION_TYPES = {
    "interval": IntervalConfig,
    "digraph_multipliers": DigraphMultipliers,
    "hold": HoldConfig,
    "rollover": RolloverConfig,
    "burst": BurstConfig,
    "cognitive_pauses": CognitivePauseConfig,
    "fatigue": FatigueConfig,
    "pace": PaceConfig,
    "errors": ErrorConfig,
    "mouse": MouseConfig,
}


def _build_section(cls, data: dict):
    known = {f.name for f in fields(cls)}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"unknown keys for [{cls.__name__}]: {sorted(unknown)}")
    kwargs = dict(data)
    if "detection_delay_chars" in kwargs:
        kwargs["detection_delay_chars"] = tuple(kwargs["detection_delay_chars"])
    return cls(**kwargs)


def _load_toml(data: dict) -> Profile:
    kwargs: dict = {}
    for key, value in data.items():
        if key in _SECTION_TYPES:
            kwargs[key] = _build_section(_SECTION_TYPES[key], value)
        else:
            kwargs[key] = value
    profile = Profile(**kwargs)
    _validate(profile)
    return profile


def load(name_or_path: str) -> Profile:
    """Load a profile by shipped name (e.g. "touch_typist") or by path to a
    .toml file.
    """
    path = pathlib.Path(name_or_path)
    if not path.suffix:
        path = _PROFILES_DIR / f"{name_or_path}.toml"
    if not path.exists():
        available = sorted(p.stem for p in _PROFILES_DIR.glob("*.toml"))
        raise FileNotFoundError(f"profile {name_or_path!r} not found. Available: {available}")
    with open(path, "rb") as f:
        data = _toml.load(f)
    return _load_toml(data)


def loads(text: str) -> Profile:
    """Load a profile from an in-memory TOML string."""
    return _load_toml(_toml.loads(text))


def available_profiles() -> list[str]:
    return sorted(p.stem for p in _PROFILES_DIR.glob("*.toml"))


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, (tuple, list)):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    return repr(v) if isinstance(v, float) else str(v)


def to_toml(p: Profile) -> str:
    """Serialize a Profile back to the plain-data TOML format shipped
    profiles use. Used by `humaninput fit` to write out a fitted profile.
    """
    lines = [f"name = {_toml_value(p.name)}", f"wpm_target = {_toml_value(p.wpm_target)}", f"layout = {_toml_value(p.layout)}", ""]
    for section_name in _SECTION_TYPES:
        section = getattr(p, section_name)
        lines.append(f"[{section_name}]")
        for f in fields(section):
            lines.append(f"{f.name} = {_toml_value(getattr(section, f.name))}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _validate(p: Profile) -> None:
    if p.wpm_target <= 0:
        raise ValueError("wpm_target must be positive")
    if p.interval.distribution != "lognormal":
        raise ValueError(f"unsupported interval distribution: {p.interval.distribution!r}")
    if p.errors.correction_strategy not in ("immediate", "word", "ignore"):
        raise ValueError(f"unsupported correction_strategy: {p.errors.correction_strategy!r}")
    for rate_name in (
        "substitution_rate",
        "transposition_rate",
        "insertion_rate",
        "omission_rate",
        "uncorrected_rate",
        "arrow_correction_probability",
        "retype_error_rate_multiplier",
    ):
        v = getattr(p.errors, rate_name)
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"errors.{rate_name} must be in [0, 1], got {v}")
    if p.errors.arrow_correction_max_tail < 0:
        raise ValueError("errors.arrow_correction_max_tail must be >= 0")
    if p.errors.max_cascade_depth < 0:
        raise ValueError("errors.max_cascade_depth must be >= 0")
    lo, hi = p.errors.detection_delay_chars
    if lo < 0 or hi < lo:
        raise ValueError("errors.detection_delay_chars must be [min, max] with 0 <= min <= max")
    if p.pace.min_multiplier <= 0 or p.pace.max_multiplier < p.pace.min_multiplier:
        raise ValueError("pace.min_multiplier must be > 0 and <= pace.max_multiplier")
