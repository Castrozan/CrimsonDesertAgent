import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GroundVector:
    x: float
    z: float

    @staticmethod
    def from_world(vector: list[float]) -> "GroundVector":
        return GroundVector(vector[0], vector[2])

    def length(self) -> float:
        return math.hypot(self.x, self.z)

    def normalized(self) -> "GroundVector":
        length = self.length()
        if length == 0:
            raise ValueError("cannot normalize a zero ground vector")
        return GroundVector(self.x / length, self.z / length)

    def dot(self, other: "GroundVector") -> float:
        return self.x * other.x + self.z * other.z

    def minus(self, other: "GroundVector") -> "GroundVector":
        return GroundVector(self.x - other.x, self.z - other.z)


@dataclass(frozen=True)
class StickDeflection:
    right: float
    forward: float


def stick_toward(
    player: GroundVector,
    target: GroundVector,
    camera_forward: GroundVector,
    camera_right: GroundVector,
    full_speed_distance: float,
    minimum_magnitude: float,
) -> StickDeflection:
    offset = target.minus(player)
    distance = offset.length()
    if distance == 0:
        return StickDeflection(0.0, 0.0)
    direction = offset.normalized()
    forward_axis = camera_forward.normalized()
    right_axis = camera_right.normalized()
    right = direction.dot(right_axis)
    forward = direction.dot(forward_axis)
    largest = max(abs(right), abs(forward))
    magnitude = max(minimum_magnitude, min(1.0, distance / full_speed_distance))
    return StickDeflection(right / largest * magnitude, forward / largest * magnitude)


def heading_degrees(direction: GroundVector) -> float:
    return math.degrees(math.atan2(direction.x, direction.z)) % 360.0


def turn_degrees(current_heading: float, target_heading: float) -> float:
    return (target_heading - current_heading + 180.0) % 360.0 - 180.0


def pitch_degrees(forward: list[float]) -> float:
    length = math.sqrt(sum(component * component for component in forward))
    if length == 0:
        raise ValueError("cannot take the pitch of a zero vector")
    return math.degrees(math.asin(max(-1.0, min(1.0, forward[1] / length))))


def interpolate(points: tuple[tuple[float, float], ...], x: float) -> float:
    if x <= points[0][0]:
        return points[0][1]
    for (left_x, left_y), (right_x, right_y) in zip(points, points[1:]):
        if x <= right_x:
            return left_y + (right_y - left_y) * (x - left_x) / (right_x - left_x)
    return points[-1][1]
