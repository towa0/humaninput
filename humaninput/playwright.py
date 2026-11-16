"""Type into a Playwright locator with a seeded, human-like event stream.

Sync API only, matching `humaninput.backends.browser`. Playwright is never
imported at runtime: the caller passes in a live `Locator`, and this module
only calls methods on it.

```python
from humaninput.playwright import type_into

stream = type_into(page.get_by_role("searchbox"), "Amsterdam", profile="hunt_and_peck", seed=13)
```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from humaninput import profile as profiles_mod
from humaninput.backends import browser
from humaninput.events import EventStream
from humaninput.layout import Layout
from humaninput.profile import Profile
from humaninput.typing.typist import Typist

if TYPE_CHECKING:
    from playwright.sync_api import Locator


def type_into(
    locator: Locator,
    text: str,
    *,
    profile: str | Profile = "touch_typist",
    seed: int | None = None,
    errors: bool = True,
    layout: Layout | str | None = None,
) -> EventStream:
    """Click `locator`, then type `text` into it with the timing of a
    generated `EventStream`. Returns the stream so a test can log it.

    The field is clicked rather than focused, because people click a field
    before typing into it, and apps often react to that click (opening a
    dropdown, selecting text). The click goes through Playwright's normal
    actionability checks. Clicking puts the caret where the click lands, so
    clear a field that already has text before calling this.

    `profile` is a shipped profile name, a path to a profile TOML, or a
    `Profile`. `seed=None` gives a different stream on every call.
    """
    if isinstance(profile, str):
        profile = profiles_mod.load(profile)
    stream = Typist(profile=profile, seed=seed, layout=layout).type(text, errors=errors)
    locator.click()
    browser.play_keys(stream, locator.page)
    return stream
