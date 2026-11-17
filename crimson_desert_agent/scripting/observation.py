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


SUMMARIZED_ELSEWHERE = frozenset(
    {
        "sequence",
        "uptime_ms",
        "in_world",
        "player",
        "player_status",
        "camera",
        "camera_status",
    }
)
SUMMARIZED_PLAYER_FIELDS = frozenset(
    {
        "position",
        "rotation",
        "health",
        "health_max",
        "stamina",
        "stamina_max",
        "static_position_error",
    }
)


class ActorNotListed(Exception):
    pass


def listed_actor(state: dict, key: str) -> dict:
    for actor in state.get("actors") or []:
        if key in (str(actor.get("key")), actor.get("kind")):
            return actor
    raise ActorNotListed(
        f"no actor {key!r} in the bridge state; give a key or a kind that status lists"
    )


def compact_actor(actor: dict) -> dict:
    compact = dict(actor)
    if isinstance(actor.get("position"), list):
        compact["position"] = [round(component, 1) for component in actor["position"]]
    if isinstance(actor.get("distance"), (int, float)):
        compact["distance"] = round(actor["distance"], 1)
    return compact


def summarize(state: dict, nearest_actors: int | None = None) -> dict:
    described = with_camera_angles(state)
    player = described.get("player") or {}
    newer_fields = {
        key: value
        for key, value in described.items()
        if key not in SUMMARIZED_ELSEWHERE
    }
    newer_player_fields = {
        key: value
        for key, value in player.items()
        if key not in SUMMARIZED_PLAYER_FIELDS
    }
    if isinstance(newer_fields.get("actors"), list):
        actors = newer_fields["actors"]
        newer_fields["actors"] = [
            compact_actor(actor) for actor in actors[:nearest_actors]
        ]
        newer_fields["actors_in_range"] = len(actors)
    return {
        "in_world": described.get("in_world"),
        "position": player.get("position"),
        "health": player.get("health"),
        **newer_player_fields,
        **newer_fields,
    }


def ground_speed(before: dict, after: dict, seconds: float) -> float | None:
    if not before.get("player") or not after.get("player"):
        return None
    travelled = GroundVector.from_world(after["player"]["position"]).minus(
        GroundVector.from_world(before["player"]["position"])
    )
    return round(travelled.length() / seconds, 2)
