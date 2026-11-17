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
