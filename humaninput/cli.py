"""Command-line interface. See README for usage examples."""

from __future__ import annotations

import argparse
import sys
import time

from humaninput import fitting
from humaninput import profile as profiles_mod
from humaninput.events import KeyAction
from humaninput.layout import available_layouts
from humaninput.mouse.pointer import Pointer
from humaninput.typing.typist import Typist


def _parse_xy(s: str) -> tuple[float, float]:
    x, y = s.split(",")
    return float(x), float(y)


def _write_output(text: str, output: str | None) -> None:
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")


def cmd_type(args: argparse.Namespace) -> int:
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    elif args.text is not None:
        text = args.text
    else:
        text = sys.stdin.read()

    profile = profiles_mod.load(args.profile)
    layout = args.layout or profile.layout
    typist = Typist(profile=profile, seed=args.seed, layout=layout)
    stream = typist.type(text, errors=not args.no_errors)

    if args.backend == "terminal":
        from humaninput.backends import terminal

        terminal.play(stream, speed=args.speed)
    elif args.backend == "json":
        from humaninput.backends import json as json_backend

        _write_output(json_backend.to_json(stream), args.output)
    elif args.backend == "svg":
        from humaninput.backends import svg as svg_backend

        _write_output(svg_backend.render(stream), args.output)
    elif args.backend == "css":
        from humaninput.backends import css_keyframes

        _write_output(css_keyframes.render(stream), args.output)
    elif args.backend == "asciinema":
        from humaninput.backends import asciinema

        if not args.output:
            print("error: --backend asciinema requires -o/--output", file=sys.stderr)
            return 2
        asciinema.write(stream, args.output)
    elif args.backend == "pynput":
        from humaninput.backends import pynput as pynput_backend

        pynput_backend.play_keys(stream)
    else:
        print(f"unknown backend: {args.backend}", file=sys.stderr)
        return 2
    return 0


def cmd_mouse(args: argparse.Namespace) -> int:
    profile = profiles_mod.load(args.profile)
    pointer = Pointer(profile=profile, seed=args.seed)
    from_xy = _parse_xy(args.from_)
    to_xy = _parse_xy(args.to)

    if args.action == "move":
        stream = pointer.move(from_xy, to_xy, target_width=args.target_width)
    elif args.action == "drag":
        stream = pointer.drag(from_xy, to_xy, target_width=args.target_width)
    elif args.action == "click":
        stream = pointer.click(*to_xy)
    elif args.action == "dblclick":
        stream = pointer.double_click(*to_xy)
    else:
        print(f"unknown action: {args.action}", file=sys.stderr)
        return 2

    if args.backend == "json":
        from humaninput.backends import json as json_backend

        _write_output(json_backend.to_json(stream), args.output)
    elif args.backend == "matplotlib":
        from humaninput.backends import matplotlib as mpl_backend

        mpl_backend.plot_trajectory(stream, show=True)
    elif args.backend == "pynput":
        from humaninput.backends import pynput as pynput_backend

        pynput_backend.play_mouse(stream)
    else:
        print(f"unknown backend: {args.backend}", file=sys.stderr)
        return 2
    return 0


def cmd_fit(args: argparse.Namespace) -> int:
    fitted = fitting.fit_csv(args.csv, name=args.name, layout_name=args.layout)
    toml_text = profiles_mod.to_toml(fitted)
    _write_output(toml_text, args.output)
    return 0


def cmd_write_on_hotkey(args: argparse.Namespace) -> int:
    from humaninput.tools import shadow_writer

    shadow_writer.run(
        args.file,
        hotkey=args.hotkey,
        cancel_hotkey=args.cancel_hotkey,
        quit_hotkey=args.quit_hotkey,
        profile_name=args.profile,
        seed=args.seed,
        layout_name=args.layout,
        start_delay_s=args.delay,
        errors=not args.no_errors,
    )
    return 0


def cmd_click_type(args: argparse.Namespace) -> int:
    from humaninput.tools import automate

    profile = profiles_mod.load(args.profile)
    to_xy = _parse_xy(args.to)
    from_xy = _parse_xy(args.from_) if args.from_ else None
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    elif args.text is not None:
        text = args.text
    else:
        text = sys.stdin.read()

    print(f"[click-type] acting in {args.delay:.1f}s ... switch to the target window now", file=sys.stderr)
    for remaining in range(int(args.delay), 0, -1):
        print(f"  {remaining}...", file=sys.stderr)
        time.sleep(1.0)

    automate.click_and_type(
        profile,
        to_xy,
        text,
        from_xy=from_xy,
        seed=args.seed,
        layout=args.layout,
        errors=not args.no_errors,
    )
    return 0


def cmd_profiles(args: argparse.Namespace) -> int:
    print("profiles:")
    for name in profiles_mod.available_profiles():
        print(f"  {name}")
    print("layouts:")
    for name in available_layouts():
        print(f"  {name}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    import numpy as np

    from humaninput.layout import load_layout

    profile = profiles_mod.load(args.profile)
    load_layout(profile.layout)
    print(f"validating profile {profile.name!r}\n")
    ok = True

    text = (
        "the quick brown fox jumps over the lazy dog and then runs away quickly into the "
        "forest before anyone notices what happened next in this rather long sentence "
    ) * 4
    stream = Typist(profile=profile, seed=1234).type(text, errors=False)
    measured_wpm = (len(text) / 5) / (stream.duration_ms / 1000 / 60)
    tolerance = 0.30
    wpm_ok = profile.wpm_target * (1 - tolerance) <= measured_wpm <= profile.wpm_target * (1 + tolerance)
    ok &= wpm_ok
    print(f"[{'PASS' if wpm_ok else 'FAIL'}] measured WPM {measured_wpm:.1f} vs target {profile.wpm_target} (+/-{tolerance:.0%})")

    def mean_interval(pair: str) -> float:
        import copy

        isolated = copy.deepcopy(profile)
        isolated.burst.mean_length = 1_000_000.0
        isolated.rollover.probability = 0.0
        isolated.cognitive_pauses.rare_word_probability = 0.0
        isolated.cognitive_pauses.digit_probability = 0.0
        isolated.cognitive_pauses.bracket_probability = 0.0
        isolated.cognitive_pauses.sentence_start_probability = 0.0
        isolated.pace.enabled = False
        isolated.fatigue.enabled = False
        s = Typist(profile=isolated, seed=99).type(pair * 1500, errors=False)
        downs = [e.t_ms for e in s.events if e.action == KeyAction.DOWN]
        return float(np.mean([b - a for a, b in zip(downs, downs[1:])]))

    same_key = mean_interval("l")
    alternating = mean_interval("th")
    same_hand = mean_interval("er")
    same_finger = mean_interval("ed")
    ordering_ok = same_key < alternating < same_hand < same_finger
    ok &= ordering_ok
    print(f"[{'PASS' if ordering_ok else 'FAIL'}] digraph ordering: same_key={same_key:.0f} < alternating={alternating:.0f} < same_hand={same_hand:.0f} < same_finger={same_finger:.0f}")

    a = Typist(profile=profile, seed=42).type("reproducibility check")
    b = Typist(profile=profile, seed=42).type("reproducibility check")
    repro_ok = a.events == b.events
    ok &= repro_ok
    print(f"[{'PASS' if repro_ok else 'FAIL'}] seeded reproducibility")

    try:
        import copy

        from scipy import stats

        isolated = copy.deepcopy(profile)
        isolated.burst.mean_length = 1_000_000.0
        isolated.rollover.probability = 0.0
        isolated.cognitive_pauses.rare_word_probability = 0.0
        isolated.cognitive_pauses.digit_probability = 0.0
        isolated.cognitive_pauses.bracket_probability = 0.0
        isolated.cognitive_pauses.sentence_start_probability = 0.0
        isolated.pace.enabled = False
        isolated.fatigue.enabled = False

        median = isolated.interval.mu_ms * isolated.digraph_multipliers.same_key
        s = Typist(profile=isolated, seed=7).type("l" * 3000, errors=False)
        downs = [e.t_ms for e in s.events if e.action == KeyAction.DOWN]
        intervals = [b - a for a, b in zip(downs, downs[1:])]
        _, pvalue = stats.kstest(intervals, "lognorm", args=(isolated.interval.sigma, 0, median))
        ks_ok = pvalue > 0.01
        ok &= ks_ok
        print(f"[{'PASS' if ks_ok else 'FAIL'}] KS test vs configured log-normal (p={pvalue:.3f})")
    except ImportError:
        print("[SKIP] KS test (scipy not installed)")

    print(f"\n{'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'}")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="humaninput", description="Model human input timing as a statistical process.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_type = sub.add_parser("type", help="Generate typing events and replay/export them.")
    p_type.add_argument("text", nargs="?", help="Text to type. Reads stdin if omitted and -f not given.")
    p_type.add_argument("-f", "--file", help="Read text to type from a file.")
    p_type.add_argument("--profile", default="touch_typist", help="Profile name or path (default: touch_typist).")
    p_type.add_argument("--layout", default=None, help="Keyboard layout override (default: from profile).")
    p_type.add_argument("--seed", type=int, default=None, help="Random seed for reproducible output.")
    p_type.add_argument("--speed", type=float, default=1.0, help="Terminal backend playback speed multiplier.")
    p_type.add_argument("--no-errors", action="store_true", help="Disable typo/correction simulation.")
    p_type.add_argument(
        "--backend", default="terminal", choices=["terminal", "json", "svg", "css", "asciinema", "pynput"], help="Output backend."
    )
    p_type.add_argument("-o", "--output", default=None, help="Write to file instead of stdout (svg/json/css/asciinema).")
    p_type.set_defaults(func=cmd_type)

    p_mouse = sub.add_parser("mouse", help="Generate mouse-movement events and export them.")
    p_mouse.add_argument("--from", dest="from_", required=True, help="Start position, e.g. 100,100")
    p_mouse.add_argument("--to", required=True, help="End position, e.g. 800,600")
    p_mouse.add_argument("--target-width", type=float, default=40.0, help="Fitts's law target width in px.")
    p_mouse.add_argument("--action", default="move", choices=["move", "drag", "click", "dblclick"])
    p_mouse.add_argument("--profile", default="touch_typist")
    p_mouse.add_argument("--seed", type=int, default=None)
    p_mouse.add_argument("--backend", default="json", choices=["json", "matplotlib", "pynput"])
    p_mouse.add_argument("-o", "--output", default=None)
    p_mouse.set_defaults(func=cmd_mouse)

    p_fit = sub.add_parser("fit", help="Fit a profile from a CSV of recorded keystroke timings.")
    p_fit.add_argument("csv", help="CSV with columns timestamp_ms,key,action")
    p_fit.add_argument("-o", "--output", default=None, help="Write fitted profile TOML to this path (default: stdout).")
    p_fit.add_argument("--name", default="fitted", help="Name for the fitted profile.")
    p_fit.add_argument("--layout", default="qwerty", help="Layout to classify digraphs against.")
    p_fit.set_defaults(func=cmd_fit)

    p_hotkey = sub.add_parser(
        "write-on-hotkey", help="Listen for a global hotkey and type a text file's contents wherever focus is."
    )
    p_hotkey.add_argument("file", help="Text file to type. Re-read on every trigger.")
    p_hotkey.add_argument("--hotkey", default="<ctrl>+<alt>+h", help="Global hotkey that starts typing.")
    p_hotkey.add_argument("--cancel-hotkey", default="<ctrl>+<alt>+x", help="Global hotkey that aborts in-progress typing.")
    p_hotkey.add_argument("--quit-hotkey", default="<ctrl>+<alt>+q", help="Global hotkey that stops the listener.")
    p_hotkey.add_argument("--profile", default="touch_typist")
    p_hotkey.add_argument("--layout", default=None)
    p_hotkey.add_argument("--seed", type=int, default=None)
    p_hotkey.add_argument("--delay", type=float, default=2.5, help="Seconds to wait after the hotkey before typing starts.")
    p_hotkey.add_argument("--no-errors", action="store_true")
    p_hotkey.set_defaults(func=cmd_write_on_hotkey)

    p_click_type = sub.add_parser("click-type", help="Move the real mouse to a point, click it, then type text there.")
    p_click_type.add_argument("--to", required=True, help="Target position to click, e.g. 500,300")
    p_click_type.add_argument("--from", dest="from_", default=None, help="Start position (default: current cursor position)")
    p_click_type.add_argument("text", nargs="?", help="Text to type. Reads -f/--file if omitted.")
    p_click_type.add_argument("-f", "--file", help="Read text to type from a file.")
    p_click_type.add_argument("--profile", default="touch_typist")
    p_click_type.add_argument("--layout", default=None)
    p_click_type.add_argument("--seed", type=int, default=None)
    p_click_type.add_argument("--delay", type=float, default=3.0, help="Seconds to wait before acting (time to switch to the target window).")
    p_click_type.add_argument("--no-errors", action="store_true")
    p_click_type.set_defaults(func=cmd_click_type)

    p_profiles = sub.add_parser("profiles", help="List available profiles and layouts.")
    p_profiles.set_defaults(func=cmd_profiles)

    p_validate = sub.add_parser("validate", help="Run statistical validation checks against a profile.")
    p_validate.add_argument("--profile", default="touch_typist")
    p_validate.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
