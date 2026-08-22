"""Emit a CSS @keyframes animation that types text into an element's
`::after { content }`. `content` is not an animatable property, so the
browser switches it discretely at each keyframe percentage instead of
interpolating — exactly the "reveal one state, then the next" behavior we
want, including corrections (a keyframe's content can be shorter than the
previous one).
"""

from __future__ import annotations

from humaninput.events import EventStream, KeyAction


def _replay_states(stream: EventStream) -> list[tuple[float, str]]:
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


def _css_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def render(
    stream: EventStream,
    class_name: str = "humaninput-typing",
    loop: bool = True,
    loop_pause_ms: float = 900.0,
    cursor: bool = True,
) -> str:
    states = _replay_states(stream)
    total_ms = (states[-1][0] + loop_pause_ms) if states else loop_pause_ms

    keyframe_lines = []
    seen_pct: set[str] = set()
    for t_ms, text in states:
        pct = 0.0 if total_ms <= 0 else (t_ms / total_ms) * 100
        pct_str = f"{pct:.3f}"
        if pct_str in seen_pct:
            continue
        seen_pct.add(pct_str)
        keyframe_lines.append(f'  {pct_str}% {{ content: "{_css_escape(text)}"; }}')
    if "100.000" not in seen_pct:
        keyframe_lines.append(f'  100% {{ content: "{_css_escape(states[-1][1] if states else "")}"; }}')

    duration_s = total_ms / 1000.0
    iteration = "infinite" if loop else "1"

    css = f"""@keyframes {class_name}-content {{
{chr(10).join(keyframe_lines)}
}}

.{class_name} {{
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: pre;
}}

.{class_name}::after {{
  content: "";
  animation: {class_name}-content {duration_s:.3f}s steps(1, end) {iteration};
}}"""

    if cursor:
        css += f"""

@keyframes {class_name}-cursor {{
  0%, 45% {{ opacity: 1; }}
  50%, 100% {{ opacity: 0; }}
}}

.{class_name}::before {{
  content: "\\2588";
  animation: {class_name}-cursor 1.05s steps(1, end) infinite;
}}"""

    return css
