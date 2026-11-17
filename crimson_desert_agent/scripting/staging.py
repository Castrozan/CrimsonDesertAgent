from dataclasses import dataclass

from .navigation import GroundVector


@dataclass(frozen=True)
class Stage:
    start: tuple[float, float, float]
    end: tuple[float, float]


class NothingToStageAgainst(Exception):
    pass


def stage_across_view(
    state: dict, ahead_m: float, from_right_m: float, to_right_m: float
) -> Stage:
    camera, player = state.get("camera"), state.get("player")
    if not camera or not player:
        raise NothingToStageAgainst(
            "the player is not in the world, so there is no camera to stage against"
        )
    forward = GroundVector.from_world(camera["forward"]).normalized()
    right = GroundVector.from_world(camera["right"]).normalized()
    eye = GroundVector.from_world(camera["position"])

    def point(right_m: float) -> tuple[float, float]:
        return (
            round(eye.x + forward.x * ahead_m + right.x * right_m, 3),
            round(eye.z + forward.z * ahead_m + right.z * right_m, 3),
        )

    start_x, start_z = point(from_right_m)
    return Stage((start_x, round(player["position"][1], 3), start_z), point(to_right_m))


def copy_error(peer_state: dict, bridge_state: dict) -> dict:
    copies = [
        actor
        for actor in bridge_state.get("actors") or []
        if actor.get("kind") == "coop_copy"
    ]
    if not copies:
        return {"copy_visible": False}
    body, copy = peer_state["position"], copies[0]["position"]
    ground = GroundVector(copy[0] - body[0], copy[2] - body[2]).length()
    return {
        "copy_visible": True,
        "ground_error_m": round(ground, 3),
        "height_error_m": round(copy[1] - body[1], 3),
        "peer_position": body,
        "copy_position": copy,
        "copy_key": copies[0].get("key"),
    }
