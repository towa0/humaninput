"""humaninput: model human input timing as a statistical process, emitted
as a timed event stream. No I/O in the core — backends consume the stream.
"""

from humaninput import profile as profiles
from humaninput.events import EventStream, KeyEvent, MouseEvent
from humaninput.mouse.pointer import Pointer
from humaninput.profile import Profile
from humaninput.typing.typist import Typist

__version__ = "0.1.0"

__all__ = [
    "Typist",
    "Pointer",
    "Profile",
    "KeyEvent",
    "MouseEvent",
    "EventStream",
    "profiles",
]
