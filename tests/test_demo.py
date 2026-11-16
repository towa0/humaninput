"""The docs demo replays the real component with streams from the engine."""

from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO = ROOT / "docs" / "demo"
EXAMPLE = ROOT / "examples" / "autocomplete-race"


def _gen():
    spec = importlib.util.spec_from_file_location("gen_demo_streams", ROOT / "scripts" / "gen_demo_streams.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _text(path: pathlib.Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def test_demo_component_is_identical_to_example():
    assert (DEMO / "autocomplete.js").read_bytes() == (EXAMPLE / "autocomplete.js").read_bytes(), (
        "copy examples/autocomplete-race/autocomplete.js to docs/demo/"
    )


def test_demo_streams_are_up_to_date():
    assert _text(DEMO / "streams.js") == _gen().build(), "run python scripts/gen_demo_streams.py"


def _streams() -> dict:
    s = _text(DEMO / "streams.js")
    return json.loads(s[s.index("=") + 1 :].strip().rstrip(";"))


@pytest.mark.browser
@pytest.mark.parametrize(
    ("seed", "fixed", "passes"),
    [(7, False, False), (0, False, True), (7, True, True)],
    ids=["seed=7", "seed=0", "seed=7-fixed"],
)
def test_demo_outcome(seed, fixed, passes):
    sync_api = pytest.importorskip("playwright.sync_api")
    duration = next(s["duration_ms"] for s in _streams()["streams"] if s["seed"] == seed)
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium not available: {exc}")
        page = b.new_page()
        page.clock.install(time=0)
        page.clock.pause_at(1)
        page.goto((DEMO / "index.html").as_uri())
        page.select_option("#seed", str(seed))
        page.set_checked("#fixed", fixed)
        page.click("#play")
        page.clock.run_for(round(duration) + 1600)
        left = page.text_content("#left-verdict")
        right = page.text_content("#right-verdict")
        running = page.evaluate("'running' in document.body.dataset")
        b.close()

    assert not running
    assert left.startswith("✓ Test passes")
    if passes:
        assert right == "✓ Test passes: shows results for Amsterdam"
    else:
        assert right == "✗ Shows results for Amsterd, but you typed Amsterdam"
