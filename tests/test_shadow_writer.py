"""shadow_writer drives the real keyboard via a global hotkey listener, so
none of this can touch actual pynput in a test run. Tests fake out
`pynput` (and `pynput.keyboard`) in `sys.modules`, fake the wall clock so
`_type_cancelable`'s busy-wait loop doesn't actually block, and run
`threading.Thread` synchronously so `run()`'s hotkey callbacks can be
exercised without real threads.
"""

from __future__ import annotations

import sys
import threading
import types

import pytest

from humaninput import profile as profiles
from humaninput.events import EventStream, KeyAction, KeyEvent
from humaninput.tools import shadow_writer

_PROFILE = profiles.load("touch_typist")


class _FakeClock:
    """Deterministic stand-in for `time.perf_counter`/`time.sleep` so the
    real-time busy-wait in `_type_cancelable` resolves instantly."""

    def __init__(self) -> None:
        self.t = 0.0

    def perf_counter(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


class _FakeKey:
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"Key.{self.name}"


class _FakeController:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def press(self, key) -> None:
        self.calls.append(("press", key))

    def release(self, key) -> None:
        self.calls.append(("release", key))


def _install_fake_pynput_keyboard(monkeypatch, controller):
    fake_keys = types.SimpleNamespace(
        backspace=_FakeKey("backspace"),
        enter=_FakeKey("enter"),
        tab=_FakeKey("tab"),
        space=_FakeKey("space"),
        left=_FakeKey("left"),
        right=_FakeKey("right"),
    )
    fake_keyboard_mod = types.ModuleType("pynput.keyboard")
    fake_keyboard_mod.Controller = lambda: controller
    fake_keyboard_mod.Key = fake_keys
    fake_pynput_mod = types.ModuleType("pynput")
    fake_pynput_mod.keyboard = fake_keyboard_mod
    monkeypatch.setitem(sys.modules, "pynput", fake_pynput_mod)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", fake_keyboard_mod)
    return fake_keys


def test_read_text_reads_file(tmp_path):
    p = tmp_path / "snippet.txt"
    p.write_text("hello there", encoding="utf-8")
    assert shadow_writer._read_text(str(p)) == "hello there"


def test_type_cancelable_presses_and_releases_keys_in_order(monkeypatch):
    controller = _FakeController()
    fake_keys = _install_fake_pynput_keyboard(monkeypatch, controller)

    clock = _FakeClock()
    monkeypatch.setattr(shadow_writer.time, "perf_counter", clock.perf_counter)
    monkeypatch.setattr(shadow_writer.time, "sleep", clock.sleep)

    stream = EventStream(
        events=[
            KeyEvent(0.0, KeyAction.DOWN, "h"),
            KeyEvent(10.0, KeyAction.UP, "h"),
            KeyEvent(20.0, KeyAction.DOWN, "backspace"),
            KeyEvent(30.0, KeyAction.UP, "backspace"),
            KeyEvent(40.0, KeyAction.DOWN, "enter"),
            KeyEvent(50.0, KeyAction.UP, "enter"),
        ]
    )
    monkeypatch.setattr(
        shadow_writer.Typist, "type", lambda self, text, errors=True: stream
    )

    cancel_event = threading.Event()
    shadow_writer._type_cancelable(
        "irrelevant", profile=_PROFILE, seed=1, layout=None, cancel_event=cancel_event, errors=True
    )

    assert controller.calls == [
        ("press", "h"),
        ("release", "h"),
        ("press", fake_keys.backspace),
        ("release", fake_keys.backspace),
        ("press", fake_keys.enter),
        ("release", fake_keys.enter),
    ]


def test_type_cancelable_returns_early_when_cancelled(monkeypatch):
    controller = _FakeController()
    _install_fake_pynput_keyboard(monkeypatch, controller)

    clock = _FakeClock()
    monkeypatch.setattr(shadow_writer.time, "perf_counter", clock.perf_counter)
    monkeypatch.setattr(shadow_writer.time, "sleep", clock.sleep)

    stream = EventStream(events=[KeyEvent(0.0, KeyAction.DOWN, "h")])
    monkeypatch.setattr(
        shadow_writer.Typist, "type", lambda self, text, errors=True: stream
    )

    cancel_event = threading.Event()
    cancel_event.set()
    shadow_writer._type_cancelable(
        "irrelevant", profile=_PROFILE, seed=1, layout=None, cancel_event=cancel_event, errors=True
    )

    assert controller.calls == []


def test_type_cancelable_raises_without_pynput(monkeypatch):
    monkeypatch.setitem(sys.modules, "pynput", None)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", None)

    with pytest.raises(RuntimeError, match="pip install humaninput\\[pynput\\]"):
        shadow_writer._type_cancelable(
            "x", profile=None, seed=1, layout=None, cancel_event=threading.Event(), errors=True
        )


def test_run_raises_without_pynput(monkeypatch):
    monkeypatch.setitem(sys.modules, "pynput", None)

    with pytest.raises(RuntimeError, match="pip install humaninput\\[pynput\\]"):
        shadow_writer.run("nope.txt")


class _FakeGlobalHotKeys:
    """Records the hotkey->callback mapping it was built with and reports
    itself as already stopped, so `run()`'s poll loop exits immediately."""

    last_instance: _FakeGlobalHotKeys | None = None

    def __init__(self, mapping: dict) -> None:
        self.mapping = mapping
        self.running = False
        self.stopped = False
        _FakeGlobalHotKeys.last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def stop(self) -> None:
        self.stopped = True


def _install_fake_pynput_for_run(monkeypatch):
    fake_keyboard_mod = types.ModuleType("pynput.keyboard")
    fake_keyboard_mod.GlobalHotKeys = _FakeGlobalHotKeys
    fake_pynput_mod = types.ModuleType("pynput")
    fake_pynput_mod.keyboard = fake_keyboard_mod
    monkeypatch.setitem(sys.modules, "pynput", fake_pynput_mod)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", fake_keyboard_mod)


def test_run_wires_hotkeys_and_stops_listener(monkeypatch, tmp_path):
    _install_fake_pynput_for_run(monkeypatch)

    shadow_writer.run(
        str(tmp_path / "unused.txt"),
        hotkey="<ctrl>+<alt>+h",
        cancel_hotkey="<ctrl>+<alt>+x",
        quit_hotkey="<ctrl>+<alt>+q",
    )

    inst = _FakeGlobalHotKeys.last_instance
    assert set(inst.mapping) == {"<ctrl>+<alt>+h", "<ctrl>+<alt>+x", "<ctrl>+<alt>+q"}
    assert inst.stopped is True


def test_run_on_trigger_types_file_contents(monkeypatch, tmp_path):
    _install_fake_pynput_for_run(monkeypatch)

    text_file = tmp_path / "snippet.txt"
    text_file.write_text("hi", encoding="utf-8")

    class _SyncThread:
        def __init__(self, target=None, daemon=None):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr(shadow_writer.threading, "Thread", _SyncThread)

    typed_texts = []
    monkeypatch.setattr(
        shadow_writer,
        "_type_cancelable",
        lambda text, profile, seed, layout, cancel_event, errors: typed_texts.append(text),
    )

    shadow_writer.run(str(text_file), start_delay_s=0)

    inst = _FakeGlobalHotKeys.last_instance
    inst.mapping["<ctrl>+<alt>+h"]()

    assert typed_texts == ["hi"]


def test_run_on_trigger_ignores_retrigger_while_typing_lock_held(monkeypatch, tmp_path, capsys):
    _install_fake_pynput_for_run(monkeypatch)

    text_file = tmp_path / "snippet.txt"
    text_file.write_text("hi", encoding="utf-8")

    calls = []

    class _SyncThread:
        def __init__(self, target=None, daemon=None):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr(shadow_writer.threading, "Thread", _SyncThread)

    def fake_type_cancelable(text, profile, seed, layout, cancel_event, errors):
        calls.append(text)

    monkeypatch.setattr(shadow_writer, "_type_cancelable", fake_type_cancelable)

    shadow_writer.run(str(text_file), start_delay_s=0)
    inst = _FakeGlobalHotKeys.last_instance
    trigger = inst.mapping["<ctrl>+<alt>+h"]

    trigger()
    assert calls == ["hi"]
    assert "already typing" not in capsys.readouterr().err
