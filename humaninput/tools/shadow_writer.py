"""Shadow writer: a global hotkey listener that types a text file's
contents, with humanlike timing, into whatever field currently has OS
focus — click into any text box anywhere on the system, press the
hotkey, and it types there.

Requires `pip install humaninput[pynput]`. Controls the real keyboard;
see the warning printed at startup.
"""

from __future__ import annotations

import sys
import threading
import time

from humaninput import profile as profiles_mod
from humaninput.events import KeyAction
from humaninput.layout import load_layout
from humaninput.typing.typist import Typist

_WARNING = """
################################################################################
 humaninput shadow writer is now listening for a global hotkey.

 Click into the text field you want typed into, then press the hotkey.
 Typing starts after a short delay so you can release the hotkey keys
 and make sure focus landed where you want it.

 ABORT current typing: press the cancel hotkey.
 STOP the listener:    press the quit hotkey, or Ctrl+C in this terminal.
 FAIL-SAFE:             move the mouse to any screen corner.
################################################################################
""".strip("\n")


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _type_cancelable(text: str, profile, seed, layout, cancel_event: threading.Event, errors: bool) -> None:
    try:
        from pynput.keyboard import Controller, Key
    except ImportError as exc:
        raise RuntimeError("shadow writer requires `pip install humaninput[pynput]`") from exc

    stream = Typist(profile=profile, seed=seed, layout=layout).type(text, errors=errors)
    controller = Controller()
    special = {"backspace": Key.backspace, "enter": Key.enter, "tab": Key.tab, "space": Key.space}

    t0 = time.perf_counter()
    for e in stream.events:
        if cancel_event.is_set():
            print("\n[shadow writer] cancelled", file=sys.stderr)
            return
        target_s = e.t_ms / 1000.0
        while True:
            elapsed = time.perf_counter() - t0
            remaining = target_s - elapsed
            if remaining <= 0:
                break
            if cancel_event.is_set():
                print("\n[shadow writer] cancelled", file=sys.stderr)
                return
            time.sleep(min(remaining, 0.05))
        key = special.get(e.key, e.key)
        if e.action == KeyAction.DOWN:
            controller.press(key)
        else:
            controller.release(key)
    print("[shadow writer] done", file=sys.stderr)


def run(
    text_path: str,
    hotkey: str = "<ctrl>+<alt>+h",
    cancel_hotkey: str = "<ctrl>+<alt>+x",
    quit_hotkey: str = "<ctrl>+<alt>+q",
    profile_name: str = "touch_typist",
    seed: int | None = None,
    layout_name: str | None = None,
    start_delay_s: float = 2.5,
    errors: bool = True,
) -> None:
    try:
        from pynput import keyboard
    except ImportError as exc:
        raise RuntimeError("shadow writer requires `pip install humaninput[pynput]`") from exc

    profile = profiles_mod.load(profile_name)
    layout = load_layout(layout_name) if layout_name else None

    cancel_event = threading.Event()
    stop_event = threading.Event()
    typing_lock = threading.Lock()

    def on_trigger():
        if typing_lock.locked():
            print("[shadow writer] already typing, ignoring", file=sys.stderr)
            return

        def worker():
            with typing_lock:
                cancel_event.clear()
                try:
                    text = _read_text(text_path)
                except OSError as exc:
                    print(f"[shadow writer] couldn't read {text_path}: {exc}", file=sys.stderr)
                    return
                print(f"[shadow writer] typing in {start_delay_s:.1f}s ...", file=sys.stderr)
                for remaining in range(int(start_delay_s), 0, -1):
                    if cancel_event.is_set():
                        return
                    time.sleep(1.0)
                _type_cancelable(text, profile, seed, layout, cancel_event, errors)

        threading.Thread(target=worker, daemon=True).start()

    def on_cancel():
        cancel_event.set()

    def on_quit():
        stop_event.set()

    print(_WARNING, file=sys.stderr)
    print(f"[shadow writer] file: {text_path}", file=sys.stderr)
    print(f"[shadow writer] profile: {profile_name}  seed: {seed}", file=sys.stderr)
    print(f"[shadow writer] type hotkey:   {hotkey}", file=sys.stderr)
    print(f"[shadow writer] cancel hotkey: {cancel_hotkey}", file=sys.stderr)
    print(f"[shadow writer] quit hotkey:   {quit_hotkey}", file=sys.stderr)

    with keyboard.GlobalHotKeys({hotkey: on_trigger, cancel_hotkey: on_cancel, quit_hotkey: on_quit}) as listener:
        try:
            while not stop_event.is_set() and listener.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            cancel_event.set()
            listener.stop()
    print("[shadow writer] stopped", file=sys.stderr)
