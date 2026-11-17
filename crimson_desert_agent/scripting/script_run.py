from dataclasses import asdict
from typing import Callable

from . import photography
from .devices import Devices
from ..story.acquaintances import Acquaintances
from ..story.confirm_guard import refuse_blind_confirm
from ..story.detour import go_around
from ..story.hazards import Hazards
from ..story.story_steps import VERBS as STORY_VERBS, StorySteps
from .observation import ground_speed, summarize
from .script import Step
from .steering import Steering
from .teaching import DEFAULT_TIMEOUT_SECONDS, teach_peer

PRESS_HOLD_SECONDS = 0.06
PRESS_GAP_SECONDS = 0.04
TURN_TOLERANCE_DEGREES = 3.0
TURN_TIMEOUT_SECONDS = 10.0
GOTO_TOLERANCE_M = 1.0
GOTO_TIMEOUT_SECONDS = 30.0
RESYNCHRONIZE_AFTER_SECONDS = 0.05
SPEED_SAMPLE_SECONDS = 0.1
ACTORS_IN_STATE = 4


class Aborted(Exception):
    pass


class ScriptRun:
    def __init__(
        self,
        devices: Devices,
        bridge,
        interrupted_within: Callable[[float], bool],
        clock: Callable[[], float],
        acquaintances: Acquaintances | None = None,
        hazards: Hazards | None = None,
    ) -> None:
        self._devices = devices
        self._pad = devices.pad
        self._bridge = bridge
        self._desktop = devices.desktop
        self._game_log = devices.game_log
        self._interrupted_within = interrupted_within
        self._clock = clock
        self._cursor = clock()
        self._hazards = hazards or Hazards()
        watched = self._hazards.watching(bridge.read_state, clock)
        self._steering = Steering(watched, devices.pad, self.pause, clock)
        self._people = acquaintances or Acquaintances()
        self._story = StorySteps(
            devices,
            bridge,
            self._steering,
            self.pause,
            clock,
            self._people,
            self._hazards,
        )
        self._hud_read_since_confirm = False

    def pause(self, seconds: float) -> None:
        now = self._clock()
        if now - self._cursor > RESYNCHRONIZE_AFTER_SECONDS:
            self._cursor = now
        self._cursor += seconds
        remaining = self._cursor - now
        if remaining > 0 and self._interrupted_within(remaining):
            raise Aborted("aborted")

    def execute(self, step: Step) -> object:
        if step.verb in STORY_VERBS:
            self._hud_read_since_confirm = True
            return getattr(self._story, step.verb)(step)
        return getattr(self, f"_{step.verb}")(step)

    def _set_controls(self, names: tuple, pressed: bool) -> None:
        seen = self._story.last_hud if self._hud_read_since_confirm else None
        if pressed and refuse_blind_confirm(names, seen, self._bridge.read_state):
            self._hud_read_since_confirm = False
        for name in names:
            self._pad.set_control(name, pressed)

    def _press(self, step: Step) -> None:
        hold = step.values[1] if len(step.values) > 1 else PRESS_HOLD_SECONDS
        gap = step.values[2] if len(step.values) > 2 else PRESS_GAP_SECONDS
        self._set_controls((step.values[0],), True)
        self.pause(hold)
        self._pad.set_control(step.values[0], False)
        self.pause(gap)

    def _down(self, step: Step) -> None:
        self._set_controls(step.rest, True)

    def _up(self, step: Step) -> None:
        self._set_controls(step.rest, False)

    def _stick(self, step: Step) -> None:
        side, right, up = step.values
        (self._pad.set_left_stick if side == "left" else self._pad.set_right_stick)(
            right, up
        )

    def _release(self, step: Step) -> None:
        self._pad.release_all()

    def _wait(self, step: Step) -> None:
        self.pause(step.values[0])

    def _hold(self, step: Step) -> None:
        self._set_controls(step.rest, True)
        self.pause(step.values[0])
        self._set_controls(step.rest, False)

    def _move(self, step: Step) -> None:
        right, forward, duration = step.values
        self._set_controls(step.rest, True)
        self._pad.set_left_stick(right, forward)
        self.pause(duration)
        self._pad.set_left_stick(0.0, 0.0)
        self._set_controls(step.rest, False)

    def _look(self, step: Step) -> None:
        right, up, duration = step.values
        self._pad.set_right_stick(right, up)
        self.pause(duration)
        self._pad.set_right_stick(0.0, 0.0)

    def _turn(self, step: Step) -> dict:
        return asdict(
            self._steering.turn_to(
                step.values[0],
                step.options.get("tolerance", TURN_TOLERANCE_DEGREES),
                step.options.get("timeout", TURN_TIMEOUT_SECONDS),
            )
        )

    def _goto(self, step: Step) -> dict:
        self._set_controls(step.rest, True)
        try:
            return go_around(
                self._steering,
                step.values[0],
                step.values[1],
                step.options.get("tolerance", GOTO_TOLERANCE_M),
                step.options.get("timeout", GOTO_TIMEOUT_SECONDS),
                self._hazards,
            )
        finally:
            self._set_controls(step.rest, False)

    def _state(self, step: Step) -> dict:
        return summarize(self._bridge.read_state(), ACTORS_IN_STATE)

    def _status(self, step: Step) -> dict:
        pad = self._pad.snapshot()
        before = self._bridge.read_state()
        self.pause(SPEED_SAMPLE_SECONDS)
        after = self._bridge.read_state()
        described = summarize(after)
        if isinstance(described.get("actors"), list):
            described["actors"] = self._people.annotate(described["actors"])
        return {
            **described,
            "ground_speed_m_per_second": ground_speed(
                before, after, SPEED_SAMPLE_SECONDS
            ),
            "game_window_focused": self._desktop.game_window_focused(),
            "pad": pad,
            "fire_hazards": self._hazards.places,
        }

    def _log(self, step: Step) -> list[str]:
        return self._game_log.new_lines()

    def _focus(self, step: Step) -> None:
        self._desktop.focus_game()

    def _shot(self, step: Step) -> dict:
        return photography.take(
            step, self._devices.camera, self._bridge.read_state, self.pause
        )

    def _hazard(self, step: Step) -> list:
        self._hazards.places.append((step.values[0], step.values[1]))
        return self._hazards.places

    def _teach(self, step: Step) -> dict:
        with self._devices.open_peer() as peer:
            return teach_peer(
                self._pad,
                peer.ask,
                self.pause,
                self._clock,
                step.options.get("timeout", DEFAULT_TIMEOUT_SECONDS),
            )
