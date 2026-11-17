from dataclasses import asdict
from typing import Callable

from . import photography
from .devices import Devices
from .hud import lines_from_words
from .observation import ground_speed, listed_actor, summarize
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
APPROACH_STANDOFF_M = 2.0


class Aborted(Exception):
    pass


class ScriptRun:
    def __init__(
        self,
        devices: Devices,
        bridge,
        interrupted_within: Callable[[float], bool],
        clock: Callable[[], float],
    ) -> None:
        self._devices = devices
        self._pad = devices.pad
        self._bridge = bridge
        self._desktop = devices.desktop
        self._game_log = devices.game_log
        self._interrupted_within = interrupted_within
        self._clock = clock
        self._cursor = clock()
        self._steering = Steering(bridge.read_state, devices.pad, self.pause, clock)

    def pause(self, seconds: float) -> None:
        now = self._clock()
        if now - self._cursor > RESYNCHRONIZE_AFTER_SECONDS:
            self._cursor = now
        self._cursor += seconds
        remaining = self._cursor - now
        if remaining > 0 and self._interrupted_within(remaining):
            raise Aborted("aborted")

    def execute(self, step: Step) -> object:
        return getattr(self, f"_{step.verb}")(step)

    def _set_controls(self, names: tuple, pressed: bool) -> None:
        for name in names:
            self._pad.set_control(name, pressed)

    def _press(self, step: Step) -> None:
        hold = step.values[1] if len(step.values) > 1 else PRESS_HOLD_SECONDS
        gap = step.values[2] if len(step.values) > 2 else PRESS_GAP_SECONDS
        self._pad.set_control(step.values[0], True)
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
            return asdict(
                self._steering.go_to(
                    step.values[0],
                    step.values[1],
                    step.options.get("tolerance", GOTO_TOLERANCE_M),
                    step.options.get("timeout", GOTO_TIMEOUT_SECONDS),
                )
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
        return {
            **summarize(after),
            "ground_speed_m_per_second": ground_speed(
                before, after, SPEED_SAMPLE_SECONDS
            ),
            "game_window_focused": self._desktop.game_window_focused(),
            "pad": pad,
        }

    def _log(self, step: Step) -> list[str]:
        return self._game_log.new_lines()

    def _focus(self, step: Step) -> None:
        self._desktop.focus_game()

    def _shot(self, step: Step) -> dict:
        return photography.take(
            step, self._devices.camera, self._bridge.read_state, self.pause
        )

    def _hud(self, step: Step) -> list[dict]:
        frame = self._devices.camera.capture()
        left, top = 0, 0
        if "crop" in step.options:
            left, top, width, height = step.options["crop"]
            frame = frame.crop((left, top, left + width, top + height))
        return lines_from_words(self._devices.read_words(frame), left, top)

    def _approach(self, step: Step) -> dict:
        actor = listed_actor(self._bridge.read_state(), step.values[0])
        self._set_controls(step.rest, True)
        try:
            return self._steering.approach(
                actor["position"],
                step.options.get("distance", APPROACH_STANDOFF_M),
                step.options.get("timeout", GOTO_TIMEOUT_SECONDS),
            )
        finally:
            self._set_controls(step.rest, False)

    def _teach(self, step: Step) -> dict:
        with self._devices.open_peer() as peer:
            return teach_peer(
                self._pad,
                peer.ask,
                self.pause,
                self._clock,
                step.options.get("timeout", DEFAULT_TIMEOUT_SECONDS),
            )
