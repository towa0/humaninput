# Tools

`humaninput/tools/` holds real-I/O automation built on the core model, which itself performs no I/O (see [Home → Core design decision](index.md#core-design-decision)). Both tools here require `pip install humaninput[pynput]` and drive the **real** OS keyboard/mouse via the `pynput` backend.

!!! warning "These control your real keyboard/mouse"
    Both tools print a warning on first use and take control of real input devices — don't touch the keyboard/mouse while a sequence plays. Both implement a fail-safe modeled on pyautogui's: if the cursor is found at a screen corner when a mouse event is about to be dispatched, playback aborts immediately with a `RuntimeError`. The `shadow_writer` also has a dedicated cancel hotkey (default `<ctrl>+<alt>+x`) for aborting mid-type without needing the corner fail-safe.

## `automate.py` — `click_and_type`

Move the mouse to a target, click it, pause briefly the way a person actually does before typing (not instantaneous), then type. Blocks for the duration of the whole sequence.

```python
from humaninput import profile as profiles
from humaninput.tools.automate import click_and_type

click_and_type(
    profiles.load("touch_typist"),
    to_xy=(500, 300),
    text="hello",
    from_xy=None,                    # defaults to the mouse's actual current position
    seed=None,                       # makes mouse path + typing reproducible (not the pause)
    button="left",
    target_width=40.0,
    pre_type_pause_ms=(150.0, 500.0),
    errors=True,
    layout=None,
)
```

`seed` only makes a single call's shape reproducible/comparable — not an entire automation session byte-for-byte, since the pre-type pause is drawn from a fresh generator each call, and the click's arrival time is affected by real wall-clock delays elsewhere in your script.

CLI equivalent:

```bash
humaninput click-type --to 500,300 "hello"
```

## `shadow_writer.py` — global-hotkey typer

A global hotkey listener: click into any text field anywhere on the system, press the hotkey, and it types a file's contents there with humanlike timing.

```python
from humaninput.tools import shadow_writer

shadow_writer.run(
    text_path="snippet.txt",
    hotkey="<ctrl>+<alt>+h",
    cancel_hotkey="<ctrl>+<alt>+x",
    quit_hotkey="<ctrl>+<alt>+q",
    profile_name="touch_typist",
    seed=None,
    layout_name=None,
    start_delay_s=2.5,               # time to switch focus after the hotkey, before typing starts
    errors=True,
)
```

The text file is **re-read on every trigger** — edit it between hotkey presses to type something different without restarting the listener. Only one typing sequence runs at a time; triggering the hotkey again while one is in progress is a no-op (logged, not queued).

CLI equivalent:

```bash
humaninput write-on-hotkey snippet.txt --hotkey "<ctrl>+<alt>+h"
```

Full flag reference for both CLI wrappers: [CLI reference](cli.md#write-on-hotkey) / [CLI reference](cli.md#click-type).
