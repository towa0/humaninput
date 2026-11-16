"""type_into without a browser: a fake Locator records the click and the CDP
calls that follow it."""

from __future__ import annotations

import subprocess
import sys

from humaninput import Typist, profiles
from humaninput.backends import browser
from humaninput.playwright import type_into


class _FakeSession:
    def __init__(self, log: list) -> None:
        self.log = log

    def send(self, method: str, params: dict) -> None:
        self.log.append((method, params))


class _FakeContext:
    def __init__(self, log: list) -> None:
        self.log = log

    def new_cdp_session(self, page) -> _FakeSession:
        return _FakeSession(self.log)


class _FakeClock:
    def __init__(self, log: list) -> None:
        self.log = log

    def run_for(self, ms: int) -> None:
        self.log.append(("run_for", ms))


class _FakePage:
    def __init__(self, log: list) -> None:
        self.context = _FakeContext(log)
        self.clock = _FakeClock(log)


class _FakeLocator:
    def __init__(self) -> None:
        self.log: list = []
        self.page = _FakePage(self.log)

    def click(self) -> None:
        self.log.append(("click", None))


def _no_sleep(monkeypatch):
    monkeypatch.setattr(browser.time, "sleep", lambda s: None)


def test_clicks_before_typing_and_returns_the_played_stream(monkeypatch):
    _no_sleep(monkeypatch)
    loc = _FakeLocator()

    stream = type_into(loc, "hello", profile="touch_typist", seed=3)

    assert loc.log[0] == ("click", None)
    sent = loc.log[1:]
    assert len(sent) == len(stream)
    assert all(method == "Input.dispatchKeyEvent" for method, _ in sent)
    expected = Typist(profile=profiles.load("touch_typist"), seed=3).type("hello")
    assert stream.events == expected.events


def test_accepts_profile_object(monkeypatch):
    _no_sleep(monkeypatch)
    p = profiles.load("hunt_and_peck")

    stream = type_into(_FakeLocator(), "abc", profile=p, seed=1)

    assert stream.profile_name == "hunt_and_peck"
    assert stream.events == Typist(profile=p, seed=1).type("abc").events


def test_errors_false_types_exact_text(monkeypatch):
    _no_sleep(monkeypatch)
    loc = _FakeLocator()

    stream = type_into(loc, "Amsterdam", profile="hunt_and_peck", seed=5, errors=False)

    typed = [p["text"] for m, p in loc.log[1:] if p["type"] == "keyDown"]
    assert "".join(typed) == "Amsterdam"
    assert not any(e.is_correction or e.is_error for e in stream)


def test_layout_is_passed_through(monkeypatch):
    _no_sleep(monkeypatch)
    p = profiles.load("touch_typist")

    stream = type_into(_FakeLocator(), "hello world", profile=p, seed=2, layout="dvorak")

    assert stream.events == Typist(profile=p, seed=2, layout="dvorak").type("hello world").events


def test_same_seed_same_stream(monkeypatch):
    _no_sleep(monkeypatch)
    a = type_into(_FakeLocator(), "Amsterdam", profile="hunt_and_peck", seed=13)
    b = type_into(_FakeLocator(), "Amsterdam", profile="hunt_and_peck", seed=13)
    assert a.events == b.events


def test_virtual_time_advances_page_clock_by_stream_gaps(monkeypatch):
    def fail_sleep(s):
        raise AssertionError("slept in virtual-time mode")

    monkeypatch.setattr(browser.time, "sleep", fail_sleep)
    loc = _FakeLocator()

    stream = type_into(loc, "hello", profile="touch_typist", seed=3, virtual_time=True)

    advanced = sum(ms for kind, ms in loc.log if kind == "run_for")
    assert advanced == round(stream.duration_ms)
    assert sum(1 for kind, _ in loc.log if kind == "Input.dispatchKeyEvent") == len(stream)


def test_real_time_is_default(monkeypatch):
    _no_sleep(monkeypatch)
    loc = _FakeLocator()
    type_into(loc, "hi", seed=1)
    assert not any(kind == "run_for" for kind, _ in loc.log)


def test_import_humaninput_does_not_import_playwright_or_pytest():
    code = (
        "import sys, humaninput, humaninput.playwright, humaninput.testing; "
        "print(sorted(m for m in ('playwright', 'pytest') if m in sys.modules))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"
