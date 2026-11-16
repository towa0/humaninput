"""The browser backend in real Chromium. Skipped when Playwright or its
Chromium build isn't installed."""

from __future__ import annotations

import pytest

from humaninput.backends import browser as browser_backend
from humaninput.events import EventStream, KeyAction, KeyEvent
from humaninput.playwright import type_into

sync_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def chromium():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium not available: {exc}")
        yield b
        b.close()


@pytest.fixture
def page(chromium):
    pg = chromium.new_page()
    yield pg
    pg.close()


def _presses(keys: list[str]) -> EventStream:
    events = []
    for i, k in enumerate(keys):
        events += [KeyEvent(i * 10.0, KeyAction.DOWN, k), KeyEvent(i * 10.0 + 5, KeyAction.UP, k)]
    return EventStream(events=events)


def test_backspace_and_arrows_edit_an_input(page):
    page.set_content("<input id=i>")
    page.click("#i")
    keys = [*"Abcd", "backspace", "arrowleft", "arrowleft", "X", "arrowright", " ", "z"]
    browser_backend.play_keys(_presses(keys), page)
    assert page.input_value("#i") == "AXb zc"


def test_newline_presses_enter_in_a_textarea(page):
    page.set_content("<textarea id=t></textarea>")
    page.click("#t")
    browser_backend.play_keys(_presses(["a", "\n", "b"]), page)
    assert page.input_value("#t") == "a\nb"


def test_virtual_time_fires_page_timers_at_stream_times(page):
    page.clock.install(time=0)
    page.clock.pause_at(1)
    page.set_content("<input id=i>")
    page.evaluate(
        "window.seen = [];"
        "document.getElementById('i').addEventListener('input', () => window.seen.push(performance.now()))"
    )

    stream = type_into(page.locator("#i"), "abc", seed=4, errors=False, virtual_time=True)

    seen = page.evaluate("window.seen")
    downs = [e.t_ms for e in stream if e.action == KeyAction.DOWN]
    assert [round(b - a) for a, b in zip(seen, seen[1:])] == [
        round(b) - round(a) for a, b in zip(downs, downs[1:])
    ]
