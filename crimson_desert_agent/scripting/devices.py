from dataclasses import dataclass
from typing import Callable, ContextManager


@dataclass(frozen=True)
class Devices:
    pad: object
    open_bridge: Callable[[], ContextManager]
    desktop: object
    camera: object
    game_log: object
    open_peer: Callable[[], ContextManager]
    read_words: Callable[[object], list]
