import copy

import pytest

from humaninput import profile as profiles


def make_isolated_profile(name: str = "touch_typist"):
    """A copy of a shipped profile with burst pauses, cognitive pauses,
    and rollover disabled, so per-keystroke interval sampling can be
    tested in isolation from the other timing effects layered on top.
    """
    p = copy.deepcopy(profiles.load(name))
    p.burst.mean_length = 1_000_000.0
    p.rollover.probability = 0.0
    p.cognitive_pauses.rare_word_probability = 0.0
    p.cognitive_pauses.digit_probability = 0.0
    p.cognitive_pauses.bracket_probability = 0.0
    p.cognitive_pauses.sentence_start_probability = 0.0
    return p


@pytest.fixture
def isolated_profile():
    return make_isolated_profile()


@pytest.fixture
def touch_typist():
    return profiles.load("touch_typist")
