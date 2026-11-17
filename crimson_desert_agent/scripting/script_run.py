from dataclasses import asdict
from typing import Callable

from .observation import summarize
from .script import Step
from .steering import Steering

PRESS_HOLD_SECONDS = 0.06
PRESS_GAP_SECONDS = 0.04
TURN_TOLERANCE_DEGREES = 3.0
TURN_TIMEOUT_SECONDS = 10.0
GOTO_TOLERANCE_M = 1.0
GOTO_TIMEOUT_SECONDS = 30.0
RESYNCHRONIZE_AFTER_SECONDS = 0.05


class Aborted(Exception):
    pass


class ScriptRun:
    def __init__(
        self,
        pad,
        bridge,
        desktop,
        game_log,
        interrupted_within: Callable[[float], bool],
        clock: Callable[[], float],
    ) -> None:
        self._pad = pad
        self._bridge = bridge
        self._desktop = desktop
        self._game_log = game_log
        self._interrupted_within = interrupted_within
        self._clock = clock
        self._cursor = clock()
        self._steering = Steering(bridge.read_state, pad, self.pause, clock)

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
        return summarize(self._bridge.read_state())

    def _log(self, step: Step) -> list[str]:
        return self._game_log.new_lines()

    def _focus(self, step: Step) -> None:
        self._desktop.focus_game()

    def _shot(self, step: Step) -> str:
        self._desktop.screenshot(step.values[0])
        return step.values[0]



