"""The browser backend's editing keys in real Chromium. Skipped when Playwright
or its Chromium build isn't installed."""

from __future__ import annotations

import pytest

from humaninput.backends import browser as browser_backend
from humaninput.events import EventStream, KeyAction, KeyEvent

sync_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def page():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium not available: {exc}")
        pg = b.new_page()
        pg.set_content("<input id=i><textarea id=t></textarea>")
        yield pg
        b.close()


def _presses(keys: list[str]) -> EventStream:
    events = []
    for i, k in enumerate(keys):
        events += [KeyEvent(i * 10.0, KeyAction.DOWN, k), KeyEvent(i * 10.0 + 5, KeyAction.UP, k)]
    return EventStream(events=events)


def test_backspace_and_arrows_edit_an_input(page):
    page.click("#i")
    keys = [*"Abcd", "backspace", "arrowleft", "arrowleft", "X", "arrowright", " ", "z"]
    browser_backend.play_keys(_presses(keys), page)
    assert page.input_value("#i") == "AXb zc"


def test_newline_presses_enter_in_a_textarea(page):
    page.click("#t")
    browser_backend.play_keys(_presses(["a", "\n", "b"]), page)
    assert page.input_value("#t") == "a\nb"
