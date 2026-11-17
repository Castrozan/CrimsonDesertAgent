from PIL import Image

from crimson_desert_agent.game.desktop import DesktopError
from crimson_desert_agent.scripting.devices import Devices
from crimson_desert_agent.scripting.engine import Engine
from crimson_desert_agent.story.screen_lines import Word
from tests.simulated_game import SimulatedGame


class RecordingDesktop:
    def __init__(self, fails: bool = False) -> None:
        self.calls: list[tuple] = []
        self.fails = fails

    def focus_game(self) -> None:
        if self.fails:
            raise DesktopError("no game window")
        self.calls.append(("focus",))

    def game_window_focused(self) -> bool:
        return not self.fails


class FixedLog:
    def new_lines(self) -> list[str]:
        return ["World: loaded"]


class RecordingCamera:
    def __init__(self) -> None:
        self.written: list[tuple] = []

    def capture(self):
        return Image.new("RGB", (1600, 900))

    def write(self, path, frames, boxes, scale, brightness) -> dict:
        self.written.append((path, len(frames), boxes, scale, brightness))
        return {"path": path, "frames": len(frames)}


class RecordingPeer:
    def __init__(self, lessons_after: int = 0) -> None:
        self.asked = 0
        self.lessons_after = lessons_after

    def __enter__(self):
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def ask(self, command: str) -> dict:
        self.asked += 1
        learnt = self.asked > self.lessons_after
        return {"ok": True, "has_move_template": learnt, "knows_walk_animation": learnt}


def engine_for(
    game: SimulatedGame,
    desktop: RecordingDesktop | None = None,
    camera=None,
    peer=None,
    read_words=None,
    read_start_actions=None,
    read_marker=None,
) -> Engine:
    devices = Devices(
        game,
        lambda: game,
        desktop or RecordingDesktop(),
        camera or RecordingCamera(),
        FixedLog(),
        lambda: peer or RecordingPeer(),
        read_words or (lambda frame: []),
        read_start_actions or (lambda last: {"ok": True, "start_actions": []}),
        read_marker or (lambda frame: None),
    )
    return Engine(devices, game.interrupted_within, game.clock)


def words(text: str, x: int, y: int) -> list[Word]:
    placed, left = [], x
    for part in text.split():
        placed.append(Word(part, left, y, left + 9 * len(part), 92.0))
        left += 9 * len(part) + 8
    return placed


def quest_block(objective: str) -> list[Word]:
    return words("Unfamiliar Lands", 60, 540) + words(objective, 76, 575)


class ScriptedScreen:
    def __init__(self, at_time) -> None:
        self.at_time = at_time
        self.game = None

    def __call__(self, frame) -> list[Word]:
        return self.at_time(self.game.now - 100.0)
