from dataclasses import dataclass
from typing import Callable, Protocol

from .navigation import (
    GroundVector,
    heading_degrees,
    interpolate,
    stick_toward,
    turn_degrees,
)

TICK_SECONDS = 0.02
FULL_SPEED_DISTANCE_M = 4.0
MINIMUM_MOVE_STICK = 0.5
PROGRESS_WINDOW_SECONDS = 3.0
MINIMUM_PROGRESS_M = 0.5
APPROACH_TOLERANCE_M = 0.5
APPROACH_FACING_TOLERANCE_DEGREES = 5.0
APPROACH_TURN_TIMEOUT_SECONDS = 8.0
CAMERA_DEGREES_PER_SECOND_BY_STICK = (
    (0.30, 0.0),
    (0.35, 2.7),
    (0.45, 11.0),
    (0.60, 34.0),
    (0.80, 87.2),
    (1.00, 143.5),
)
CAMERA_STICK_BY_DEGREES_PER_SECOND = tuple(
    (rate, stick) for stick, rate in CAMERA_DEGREES_PER_SECOND_BY_STICK
)
TURN_RATE_PER_DEGREE_OF_ERROR = 6.0
MINIMUM_TURN_RATE_DEGREES_PER_SECOND = 12.0


def look_stick_for_error(error_degrees: float) -> float:
    rate = max(
        MINIMUM_TURN_RATE_DEGREES_PER_SECOND,
        abs(error_degrees) * TURN_RATE_PER_DEGREE_OF_ERROR,
    )
    stick = interpolate(CAMERA_STICK_BY_DEGREES_PER_SECOND, rate)
    return stick if error_degrees > 0 else -stick


class Sticks(Protocol):
    def set_left_stick(self, right: float, forward: float) -> None: ...

    def set_right_stick(self, right: float, up: float) -> None: ...


@dataclass(frozen=True)
class SteeringResult:
    arrived: bool
    reason: str
    remaining: float
    elapsed_seconds: float


class NotInWorld(Exception):
    pass


class Steering:
    def __init__(
        self,
        read_state: Callable[[], dict],
        sticks: Sticks,
        pause: Callable[[float], None],
        clock: Callable[[], float],
    ) -> None:
        self._read_state = read_state
        self._sticks = sticks
        self._pause = pause
        self._clock = clock

    def _world(self) -> tuple[GroundVector, GroundVector, GroundVector]:
        state = self._read_state()
        if not state.get("player") or not state.get("camera"):
            raise NotInWorld(
                f"not in world: {state.get('player_status')} / camera {state.get('camera_status')}"
            )
        camera = state["camera"]
        return (
            GroundVector.from_world(state["player"]["position"]),
            GroundVector.from_world(camera["forward"]),
            GroundVector.from_world(camera["right"]),
        )

    def _result(self, reason: str, remaining: float, started: float) -> SteeringResult:
        return SteeringResult(
            reason == "arrived",
            reason,
            round(remaining, 3),
            round(self._clock() - started, 3),
        )

    def go_to(
        self,
        target_x: float,
        target_z: float,
        tolerance_m: float,
        timeout_seconds: float,
    ) -> SteeringResult:
        target = GroundVector(target_x, target_z)
        started = self._clock()
        progress_time, progress_distance = started, None
        distance = float("nan")
        reason = "timeout"
        try:
            while self._clock() - started < timeout_seconds:
                player, camera_forward, camera_right = self._world()
                distance = target.minus(player).length()
                if distance <= tolerance_m:
                    reason = "arrived"
                    break
                now = self._clock()
                if progress_distance is None:
                    progress_distance = distance
                elif now - progress_time >= PROGRESS_WINDOW_SECONDS:
                    if progress_distance - distance < MINIMUM_PROGRESS_M:
                        reason = f"stuck: under {MINIMUM_PROGRESS_M} m of progress in {PROGRESS_WINDOW_SECONDS} s"
                        break
                    progress_time, progress_distance = now, distance
                deflection = stick_toward(
                    player,
                    target,
                    camera_forward,
                    camera_right,
                    FULL_SPEED_DISTANCE_M,
                    MINIMUM_MOVE_STICK,
                )
                self._sticks.set_left_stick(deflection.right, deflection.forward)
                self._pause(TICK_SECONDS)
        except NotInWorld as error:
            reason = str(error)
        finally:
            self._sticks.set_left_stick(0.0, 0.0)
        return self._result(reason, distance, started)

    def approach(
        self, actor_position: list[float], standoff_m: float, timeout_seconds: float
    ) -> dict:
        actor = GroundVector.from_world(actor_position)
        offset = actor.minus(self._world()[0])
        walk = None
        if offset.length() > standoff_m + APPROACH_TOLERANCE_M:
            direction = offset.normalized()
            walk = self.go_to(
                actor.x - direction.x * standoff_m,
                actor.z - direction.z * standoff_m,
                APPROACH_TOLERANCE_M,
                timeout_seconds,
            )
        offset = actor.minus(self._world()[0])
        turn = self.turn_to(
            heading_degrees(offset),
            APPROACH_FACING_TOLERANCE_DEGREES,
            APPROACH_TURN_TIMEOUT_SECONDS,
        )
        return {
            "distance_m": round(offset.length(), 2),
            "facing": turn.arrived,
            "walk": walk.reason if walk else "already near",
        }

    def turn_to(
        self, heading: float, tolerance_degrees: float, timeout_seconds: float
    ) -> SteeringResult:
        started = self._clock()
        error = float("nan")
        reason = "timeout"
        was_within = False
        try:
            while self._clock() - started < timeout_seconds:
                _, camera_forward, _ = self._world()
                error = turn_degrees(heading_degrees(camera_forward), heading % 360.0)
                within = abs(error) <= tolerance_degrees
                if within and was_within:
                    reason = "arrived"
                    break
                was_within = within
                self._sticks.set_right_stick(
                    0.0 if within else look_stick_for_error(error), 0.0
                )
                self._pause(TICK_SECONDS)
        except NotInWorld as not_in_world:
            reason = str(not_in_world)
        finally:
            self._sticks.set_right_stick(0.0, 0.0)
        return self._result(reason, error, started)
