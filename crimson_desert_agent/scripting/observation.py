from .navigation import GroundVector, heading_degrees, pitch_degrees


def with_camera_angles(state: dict) -> dict:
    camera = state.get("camera")
    if not camera:
        return state
    described = dict(state)
    described["camera_heading_degrees"] = round(
        heading_degrees(GroundVector.from_world(camera["forward"])), 1
    )
    described["camera_pitch_degrees"] = round(pitch_degrees(camera["forward"]), 1)
    return described


def summarize(state: dict) -> dict:
    described = with_camera_angles(state)
    player = described.get("player") or {}
    return {
        "in_world": described.get("in_world"),
        "position": player.get("position"),
        "health": player.get("health"),
        "camera_heading_degrees": described.get("camera_heading_degrees"),
        "camera_pitch_degrees": described.get("camera_pitch_degrees"),
    }


def ground_speed(before: dict, after: dict, seconds: float) -> float | None:
    if not before.get("player") or not after.get("player"):
        return None
    travelled = GroundVector.from_world(after["player"]["position"]).minus(
        GroundVector.from_world(before["player"]["position"])
    )
    return round(travelled.length() / seconds, 2)
