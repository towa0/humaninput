"""click_and_type chains three real-I/O steps (move, click, type) with a
pause in between. This can't touch the real mouse/keyboard in a test
run, so it monkeypatches the pynput backend's play functions and checks
they were called in the right order with the right event streams.
"""

from __future__ import annotations

from humaninput import profile as profiles
from humaninput.backends import pynput as pynput_backend
from humaninput.events import KeyAction
from humaninput.tools import automate


def test_click_and_type_calls_move_click_then_keys_in_order(monkeypatch):
    calls = []
    monkeypatch.setattr(pynput_backend, "play_mouse", lambda stream: calls.append(("mouse", stream)))
    monkeypatch.setattr(pynput_backend, "play_keys", lambda stream: calls.append(("keys", stream)))
    monkeypatch.setattr(automate.time, "sleep", lambda s: calls.append(("sleep", s)))

    prof = profiles.load("fast_coder")
    automate.click_and_type(prof, to_xy=(500, 300), text="hi", from_xy=(0, 0), seed=1)

    kinds = [c[0] for c in calls]
    assert kinds == ["mouse", "mouse", "sleep", "keys"], kinds

    move_stream, click_stream, (_, pause_s), (_, keys_stream) = calls[0][1], calls[1][1], calls[2], calls[3]
    assert all(e.type == "move" for e in move_stream.events)
    assert any(e.type == "down" for e in click_stream.events)
    assert any(e.type == "click" for e in click_stream.events)
    assert pause_s > 0
    typed = "".join(e.key for e in keys_stream.events if e.action == KeyAction.DOWN)
    assert typed == "hi"


def test_click_and_type_defaults_from_xy_to_current_mouse_position(monkeypatch):
    monkeypatch.setattr(pynput_backend, "play_mouse", lambda stream: None)
    monkeypatch.setattr(pynput_backend, "play_keys", lambda stream: None)
    monkeypatch.setattr(automate.time, "sleep", lambda s: None)

    class _FakeController:
        position = (42.0, 7.0)

    import pynput.mouse as _mouse_mod

    monkeypatch.setattr(_mouse_mod, "Controller", _FakeController)

    captured = {}
    real_move = automate.Pointer.move

    def spy_move(self, from_xy, to_xy, target_width=40.0):
        captured["from_xy"] = from_xy
        return real_move(self, from_xy, to_xy, target_width=target_width)

    monkeypatch.setattr(automate.Pointer, "move", spy_move)

    prof = profiles.load("touch_typist")
    automate.click_and_type(prof, to_xy=(100, 100), text="x", seed=1)

    assert captured["from_xy"] == (42.0, 7.0)
