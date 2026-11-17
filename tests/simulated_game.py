import math

from crimson_desert_agent.scripting.navigation import interpolate
from crimson_desert_agent.scripting.steering import CAMERA_DEGREES_PER_SECOND_BY_STICK

from crimson_desert_agent.game.virtual_pad import CONTROL_NAMES


class SimulatedGame:
    def __init__(
        self,
        position=(0.0, 50.0, 0.0),
        camera_yaw_degrees=0.0,
        run_speed_m_per_second=6.0,
        turn_rate_scale=1.0,
        blocked=False,
        in_world=True,
    ) -> None:
        self.position = list(position)
        self.camera_yaw_degrees = camera_yaw_degrees
        self.run_speed = run_speed_m_per_second
        self.turn_rate_scale = turn_rate_scale
        self.blocked = blocked
        self.in_world = in_world
        self.left_stick = (0.0, 0.0)
        self.right_stick = (0.0, 0.0)
        self.pressed: set[str] = set()
        self.events: list[tuple[float, str, object]] = []
        self.now = 100.0
        self.abort_at: float | None = None
        self.closed_bridges = 0

    def clock(self) -> float:
        return self.now

    def interrupted_within(self, seconds: float) -> bool:
        if self.abort_at is not None and self.now + seconds >= self.abort_at:
            self.now = self.abort_at
            return True
        self.now += seconds
        yaw = math.radians(self.camera_yaw_degrees)
        if not self.blocked:
            right, forward = self.left_stick
            self.position[0] += (
                self.run_speed
                * seconds
                * (right * math.cos(yaw) + forward * math.sin(yaw))
            )
            self.position[2] += (
                self.run_speed
                * seconds
                * (-right * math.sin(yaw) + forward * math.cos(yaw))
            )
        self.camera_yaw_degrees = (
            self.camera_yaw_degrees + self.camera_rate() * seconds
        ) % 360
        return False

    def camera_rate(self) -> float:
        stick = self.right_stick[0]
        rate = interpolate(CAMERA_DEGREES_PER_SECOND_BY_STICK, abs(stick))
        return self.turn_rate_scale * (rate if stick > 0 else -rate)

    def read_state(self) -> dict:
        if not self.in_world:
            return {
                "in_world": False,
                "player": None,
                "camera": None,
                "player_status": "loading",
                "camera_status": "ok",
            }
        yaw = math.radians(self.camera_yaw_degrees)
        return {
            "in_world": True,
            "player": {"position": list(self.position), "health": 300.0},
            "player_status": "in world",
            "camera": {
                "position": [0.0, 0.0, 0.0],
                "forward": [math.sin(yaw), 0.0, math.cos(yaw)],
                "right": [math.cos(yaw), 0.0, -math.sin(yaw)],
            },
            "camera_status": "ok",
        }

    def __enter__(self) -> "SimulatedGame":
        return self

    def __exit__(self, *_: object) -> None:
        self.closed_bridges += 1

    def set_control(self, name: str, pressed: bool) -> None:
        if name not in CONTROL_NAMES:
            raise ValueError(name)
        (self.pressed.add if pressed else self.pressed.discard)(name)
        self.events.append((round(self.now - 100.0, 6), name, pressed))

    def set_left_stick(self, right: float, forward: float) -> None:
        self.left_stick = (right, forward)
        self.events.append((round(self.now - 100.0, 6), "left_stick", (right, forward)))

    def set_right_stick(self, right: float, up: float) -> None:
        self.right_stick = (right, up)
        self.events.append((round(self.now - 100.0, 6), "right_stick", (right, up)))

    def release_all(self) -> None:
        self.left_stick = (0.0, 0.0)
        self.right_stick = (0.0, 0.0)
        self.pressed.clear()
        self.events.append((round(self.now - 100.0, 6), "release_all", None))

    def snapshot(self) -> dict:
        return {
            "held": sorted(self.pressed),
            "left_stick": list(self.left_stick),
            "right_stick": list(self.right_stick),
        }

    def is_idle(self) -> bool:
        return (
            self.left_stick == (0.0, 0.0)
            and self.right_stick == (0.0, 0.0)
            and not self.pressed
        )
