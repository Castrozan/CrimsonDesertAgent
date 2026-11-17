import math
from dataclasses import dataclass

DEFAULT_VERTICAL_FIELD_OF_VIEW_DEGREES = 40.0


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    width: int
    height: int

    def clamped_to(self, width: int, height: int) -> "Box":
        box_width, box_height = min(self.width, width), min(self.height, height)
        left = max(0, min(self.left, width - box_width))
        top = max(0, min(self.top, height - box_height))
        return Box(left, top, box_width, box_height)


def dot(first: list[float], second: list[float]) -> float:
    return sum(a * b for a, b in zip(first, second))


def cross(first: list[float], second: list[float]) -> list[float]:
    return [
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    ]


def screen_point(
    camera: dict,
    world_point: list[float],
    width: int,
    height: int,
    vertical_field_of_view_degrees: float,
) -> tuple[float, float] | None:
    forward, right = camera["forward"], camera["right"]
    up = cross(forward, right)
    offset = [point - eye for point, eye in zip(world_point, camera["position"])]
    depth = dot(offset, forward)
    if depth <= 0:
        return None
    half_height = math.tan(math.radians(vertical_field_of_view_degrees) / 2)
    half_width = half_height * width / height
    horizontal = dot(offset, right) / (depth * half_width)
    vertical = dot(offset, up) / (depth * half_height)
    return (width / 2 * (1 + horizontal), height / 2 * (1 - vertical))


def box_around(point: tuple[float, float], side: int, width: int, height: int) -> Box:
    return Box(
        round(point[0] - side / 2), round(point[1] - side / 2), side, side
    ).clamped_to(width, height)
