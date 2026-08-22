"""Render typing as an animated SVG with a blinking cursor. No JS: text
reveal and correction are driven by SMIL (<set>/<animate>), which
browsers render standalone when the SVG is embedded as an <img src=...>
in a README or docs page. The whole animation loops by having a
zero-duration "clock" element restart itself and every other animation's
`begin` reference that clock's timeline (`begin="loop.begin+2.5s"`).
"""

from __future__ import annotations

from html import escape

from humaninput.events import EventStream, KeyAction


def _replay_states(stream: EventStream) -> list[tuple[float, str]]:
    """Collapse the event stream into (t_ms, buffer_text) whenever the
    visible buffer changes, replaying keydowns (and backspace deletes) in
    order.
    """
    states: list[tuple[float, str]] = [(0.0, "")]
    buf = ""
    for e in stream:
        if e.action != KeyAction.DOWN:
            continue
        if e.key == "backspace":
            buf = buf[:-1]
        elif len(e.key) == 1:
            buf += e.key
        else:
            continue
        states.append((e.t_ms, buf))
    return states


def render(
    stream: EventStream,
    font_size: int = 20,
    char_width: float | None = None,
    padding: int = 16,
    font_family: str = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
    background: str = "transparent",
    text_color: str = "#e2e8f0",
    cursor_color: str = "#4ade80",
    loop_pause_ms: float = 900.0,
) -> str:
    states = _replay_states(stream)
    char_width = char_width if char_width is not None else font_size * 0.6
    max_len = max((len(s) for _, s in states), default=0)
    width = padding * 2 + max(max_len, 1) * char_width + char_width
    height = padding * 2 + font_size * 1.3

    total_ms = states[-1][0] + loop_pause_ms if states else loop_pause_ms
    total_s = total_ms / 1000.0

    y = padding + font_size

    text_layers = []
    cursor_sets = []
    for i, (t_ms, text) in enumerate(states):
        begin_s = t_ms / 1000.0
        end_s = states[i + 1][0] / 1000.0 if i + 1 < len(states) else total_s
        text_layers.append(
            f'<text x="{padding}" y="{y}" font-family="{font_family}" '
            f'font-size="{font_size}" fill="{text_color}" opacity="0">'
            f"{escape(text)}"
            f'<set attributeName="opacity" to="1" begin="loop.begin+{begin_s:.3f}s"/>'
            f'<set attributeName="opacity" to="0" begin="loop.begin+{end_s:.3f}s"/>'
            "</text>"
        )
        cursor_x = padding + len(text) * char_width
        cursor_sets.append(f'<set attributeName="x" to="{cursor_x:.1f}" begin="loop.begin+{begin_s:.3f}s"/>')

    bg_rect = "" if background == "transparent" else f'<rect width="100%" height="100%" fill="{background}"/>'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}">
  <rect width="0" height="0">
    <animate id="loop" attributeName="opacity" from="0" to="0" dur="{total_s:.3f}s" begin="0s;loop.end"/>
  </rect>
  {bg_rect}
  {''.join(text_layers)}
  <rect x="{padding}" y="{y - font_size + 2}" width="{max(char_width * 0.55, 2):.1f}" height="{font_size}" fill="{cursor_color}">
    {''.join(cursor_sets)}
    <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.45;0.5;1" dur="1.05s" repeatCount="indefinite"/>
  </rect>
</svg>"""
    return svg


def write(stream: EventStream, path: str, **kwargs) -> None:
    svg = render(stream, **kwargs)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
