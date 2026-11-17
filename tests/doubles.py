from crimson_desert_agent.game.desktop import DesktopError
from crimson_desert_agent.scripting.devices import Devices
from crimson_desert_agent.scripting.engine import Engine
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
        return type("Frame", (), {"size": (1600, 900)})()

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
    game: SimulatedGame, desktop: RecordingDesktop | None = None, camera=None, peer=None
) -> Engine:
    devices = Devices(
        game,
        lambda: game,
        desktop or RecordingDesktop(),
        camera or RecordingCamera(),
        FixedLog(),
        lambda: peer or RecordingPeer(),
    )
    return Engine(devices, game.interrupted_within, game.clock)
