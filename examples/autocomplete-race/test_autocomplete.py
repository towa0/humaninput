"""The autocomplete race, tested four ways. See README.md in this folder.

Run from the repo root:

    pytest examples/autocomplete-race --runxfail
"""

from __future__ import annotations

import pathlib

import pytest

from humaninput.playwright import type_into
from humaninput.testing import describe, seeds

sync_api = pytest.importorskip("playwright.sync_api")

APP = (pathlib.Path(__file__).parent / "app.html").resolve().as_uri()
TEXT = "Amsterdam"
QUIET_MS = 1500

BUGGY_REASON = (
    "app.html renders whichever response arrives last; some seeds pause where a "
    "slow request gets sent. Run with --runxfail to see them fail."
)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium not available: {exc}")
        yield b
        b.close()


def _open(browser, fixed: bool):
    page = browser.new_page()
    # Virtual time: the page clock only moves when a test advances it, so
    # timers fire at exactly the typed timings, however busy the machine is.
    page.clock.install(time=0)
    page.clock.pause_at(1)
    page.goto(APP + ("?fixed=1" if fixed else ""))
    return page


@pytest.fixture
def buggy(browser):
    page = _open(browser, fixed=False)
    yield page
    page.close()


@pytest.fixture
def fixed(browser):
    page = _open(browser, fixed=True)
    yield page
    page.close()


def press_with_delay(page, text: str, delay_ms: int) -> None:
    # press_sequentially(text, delay=...) waits in real time, which a paused
    # page clock ignores. This is the same thing in virtual time.
    box = page.locator("#city")
    box.click()
    for i, ch in enumerate(text):
        if i:
            page.clock.run_for(delay_ms)
        box.press(ch)


def assert_results_match_input(page, note: str = "") -> None:
    page.clock.run_for(QUIET_MS)
    # Compare with what is in the box, not TEXT: an uncorrected typo is allowed.
    typed = page.locator("#city").input_value()
    shown = page.get_by_test_id("results-query").text_content()
    assert shown == typed, f"Shows results for {shown!r}, but you typed {typed!r}. {note}".strip()


def test_fill(buggy):
    buggy.locator("#city").fill(TEXT)
    assert_results_match_input(buggy)


def test_fixed_delay(buggy):
    press_with_delay(buggy, TEXT, 100)
    assert_results_match_input(buggy)


@pytest.mark.xfail(strict=True, reason="a fixed delay can catch this if you guess the right value")
def test_fixed_delay_slow(buggy):
    press_with_delay(buggy, TEXT, 400)
    assert_results_match_input(buggy)


@pytest.mark.xfail(strict=False, reason=BUGGY_REASON)
@pytest.mark.parametrize("seed", seeds(20))
def test_human(buggy, seed):
    stream = type_into(buggy.locator("#city"), TEXT, profile="hunt_and_peck", seed=seed, virtual_time=True)
    assert_results_match_input(buggy, describe(stream))


@pytest.mark.parametrize("seed", seeds(20))
def test_human_fixed(fixed, seed):
    stream = type_into(fixed.locator("#city"), TEXT, profile="hunt_and_peck", seed=seed, virtual_time=True)
    assert_results_match_input(fixed, describe(stream))
