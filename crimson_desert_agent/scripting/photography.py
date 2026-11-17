from typing import Callable

from .projection import DEFAULT_VERTICAL_FIELD_OF_VIEW_DEGREES, box_around, screen_point
from .script import Step

ACTOR_HEIGHT_M = 1.0
DEFAULT_ACTOR_BOX_PIXELS = 480
DEFAULT_BURST_INTERVAL_SECONDS = 0.2


class ActorNotInView(Exception):
    pass


def actor_box(
    state: dict, key: str, frame_size: tuple[int, int], side: int, field_of_view: float
):
    actors = [
        actor
        for actor in state.get("actors") or []
        if key in (actor.get("key"), actor.get("kind"))
    ]
    if not actors or not state.get("camera"):
        raise ActorNotInView(
            f"no actor {key!r} in the bridge state; give a key or a kind it lists"
        )
    position = list(actors[0]["position"])
    position[1] += ACTOR_HEIGHT_M
    point = screen_point(
        state["camera"], position, frame_size[0], frame_size[1], field_of_view
    )
    if point is None:
        raise ActorNotInView(f"actor {key!r} is behind the camera")
    box = box_around(point, side, frame_size[0], frame_size[1])
    return (box.left, box.top, box.width, box.height)


def take(
    step: Step, camera, read_state: Callable[[], dict], pause: Callable[[float], None]
) -> dict:
    options = step.options
    frames, boxes = [], []
    burst = options.get("burst", 1)
    for index in range(burst):
        frame = camera.capture()
        box = options.get("crop")
        if "actor" in options:
            box = actor_box(
                read_state(),
                options["actor"],
                frame.size,
                options.get("size", DEFAULT_ACTOR_BOX_PIXELS),
                options.get("fov", DEFAULT_VERTICAL_FIELD_OF_VIEW_DEGREES),
            )
        frames.append(frame)
        boxes.append(box)
        if index + 1 < burst:
            pause(options.get("every", DEFAULT_BURST_INTERVAL_SECONDS))
    return camera.write(
        step.values[0],
        frames,
        boxes,
        options.get("scale", 0.5),
        options.get("brightness", 1.0),
    )
