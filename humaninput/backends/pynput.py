"""Drive the real OS keyboard and mouse via `pynput`. Optional dependency
(`pip install humaninput[pynput]`), imported lazily so the core package
never requires it.

This backend takes control of real input devices. It prints a warning on
first use and implements a fail-safe modeled on pyautogui's: if the
system cursor is found at a screen corner when a mouse event is about to
be dispatched, playback aborts immediately.
"""

from __future__ import annotations

import sys
import time

from humaninput.events import EventStream, KeyAction

_warned = False

_WARNING = """
################################################################################
 humaninput: pynput backend is about to take control of your REAL keyboard
 and/or mouse. Do not touch the keyboard/mouse while this plays.

 ABORT: move the mouse to any screen corner (top-left, top-right,
 bottom-left, bottom-right) to trigger the fail-safe and stop immediately.
################################################################################
""".strip("\n")


def _warn_once() -> None:
    global _warned
    if not _warned:
        print(_WARNING, file=sys.stderr)
        _warned = True


def _check_failsafe(mouse_controller) -> None:
    try:
        import ctypes

        from pynput.mouse import Controller as MouseController  # noqa: F401

        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
        else:
            screen_w = screen_h = None
    except Exception:
        screen_w = screen_h = None

    x, y = mouse_controller.position
    corners = [(0, 0)]
    if screen_w and screen_h:
        corners += [(screen_w - 1, 0), (0, screen_h - 1), (screen_w - 1, screen_h - 1)]
    for cx, cy in corners:
        if abs(x - cx) <= 1 and abs(y - cy) <= 1:
            raise RuntimeError("humaninput pynput backend: fail-safe triggered (cursor at screen corner). Aborted.")


def play_keys(stream: EventStream) -> None:
    try:
        from pynput.keyboard import Controller, Key
    except ImportError as exc:
        raise RuntimeError("pynput backend requires `pip install humaninput[pynput]`") from exc

    _warn_once()
    controller = Controller()
    special = {
        "backspace": Key.backspace,
        "enter": Key.enter,
        "tab": Key.tab,
        "space": Key.space,
        "arrowleft": Key.left,
        "arrowright": Key.right,
    }

    t0 = time.perf_counter()
    for e in stream:
        target_s = e.t_ms / 1000.0
        elapsed = time.perf_counter() - t0
        if target_s > elapsed:
            time.sleep(target_s - elapsed)
        key = special.get(e.key, e.key)
        if e.action == KeyAction.DOWN:
            controller.press(key)
        else:
            controller.release(key)


def play_mouse(stream: EventStream) -> None:
    try:
        from pynput.mouse import Button, Controller
    except ImportError as exc:
        raise RuntimeError("pynput backend requires `pip install humaninput[pynput]`") from exc

    _warn_once()
    controller = Controller()
    buttons = {"left": Button.left, "right": Button.right, "middle": Button.middle}

    t0 = time.perf_counter()
    for e in stream:
        target_s = e.t_ms / 1000.0
        elapsed = time.perf_counter() - t0
        if target_s > elapsed:
            time.sleep(target_s - elapsed)
        _check_failsafe(controller)
        if e.type in ("move", "drag"):
            controller.position = (e.x, e.y)
        elif e.type == "down":
            controller.press(buttons.get(e.button or "left", Button.left))
        elif e.type == "up":
            controller.release(buttons.get(e.button or "left", Button.left))
        elif e.type == "scroll":
            controller.scroll(e.scroll_dx, -e.scroll_dy)
