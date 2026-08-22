"""Generate the README's lead SVG and validation plots. Not part of the
package; run manually when profiles/model change.
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from humaninput import profile as profiles
from humaninput.backends import matplotlib as mpl_backend
from humaninput.backends import svg as svg_backend
from humaninput.events import KeyAction
from humaninput.mouse.pointer import Pointer
from humaninput.typing.typist import Typist

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

prof = profiles.load("hunt_and_peck")
sentence = "realy fast typing looks fake"

chosen = None
for seed in range(200):
    stream = Typist(profile=prof, seed=seed).type(sentence, errors=True)
    n_errors = sum(1 for e in stream.events if e.is_error and e.action == KeyAction.DOWN)
    n_corrections = sum(1 for e in stream.events if e.is_correction and e.key == "backspace")
    if 1 <= n_errors <= 2 and 1 <= n_corrections <= 4 and stream.duration_ms < 18000:
        chosen = (seed, stream)
        break

assert chosen, "couldn't find a seed with a clean single visible error+correction"
seed, stream = chosen
print(f"lead SVG: seed={seed} duration={stream.duration_ms:.0f}ms")
svg = svg_backend.render(stream, font_size=22, background="#0f172a", text_color="#e2e8f0", cursor_color="#4ade80")
(DOCS / "lead.svg").write_text(svg, encoding="utf-8")

touch = profiles.load("touch_typist")
isolated = profiles.load("touch_typist")
isolated.burst.mean_length = 1_000_000.0
isolated.rollover.probability = 0.0
isolated.cognitive_pauses.rare_word_probability = 0.0
isolated.cognitive_pauses.digit_probability = 0.0
isolated.cognitive_pauses.bracket_probability = 0.0
isolated.cognitive_pauses.sentence_start_probability = 0.0
hist_stream = Typist(profile=isolated, seed=7).type("l" * 4000, errors=False)

same_key_median = isolated.interval.mu_ms * isolated.digraph_multipliers.same_key
fig = mpl_backend.plot_interval_histogram(hist_stream, profile=isolated, median_ms=same_key_median, show=False)
fig.savefig(DOCS / "interval_histogram.png", dpi=150, facecolor="white")
print("wrote interval_histogram.png")

pointer = Pointer(profile=touch, seed=4)
move_stream = pointer.move((40, 260), (760, 90), target_width=18)
fig2 = mpl_backend.plot_trajectory(move_stream, show=False)
fig2.savefig(DOCS / "mouse_trajectory.png", dpi=150, facecolor="white")
print("wrote mouse_trajectory.png")
