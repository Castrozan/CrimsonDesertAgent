from ..scripting.navigation import GroundVector

SIDESTEP_M = 4.0
SIDESTEP_TIMEOUT_SECONDS = 5.0
SIDESTEP_TOLERANCE_M = 1.0
DETOUR_ATTEMPTS = 3


RETREAT_TIMEOUT_SECONDS = 4.0
BYPASS_M = 5.0


def bypass_point(
    hazard: tuple[float, float], start: GroundVector, target: GroundVector
) -> tuple[float, float]:
    ahead = target.minus(start).normalized()
    side = (
        1.0
        if (hazard[0] - start.x) * ahead.z - (hazard[1] - start.z) * ahead.x < 0
        else -1.0
    )
    return (
        hazard[0] + side * ahead.z * BYPASS_M,
        hazard[1] - side * ahead.x * BYPASS_M,
    )


def go_around(
    steering,
    target_x: float,
    target_z: float,
    tolerance_m: float,
    timeout_seconds: float,
    hazards=None,
) -> dict:
    if hazards is not None:
        if hazards.near(target_x, target_z):
            return {
                "arrived": False,
                "reason": "refused: the target is inside a recorded fire hazard",
                "remaining": None,
                "detours": 0,
            }
        start = steering.position()
        blocking = hazards.crossed_by((start.x, start.z), (target_x, target_z))
        if blocking is not None:
            around = bypass_point(blocking, start, GroundVector(target_x, target_z))
            steering.go_to(around[0], around[1], SIDESTEP_TOLERANCE_M, timeout_seconds)
    walked = walk_with_sidesteps(
        steering, target_x, target_z, tolerance_m, timeout_seconds
    )
    if (
        hazards is not None
        and walked["reason"].startswith("burning")
        and hazards.last_safe is not None
    ):
        hazards.retreating = True
        steering.go_to(
            hazards.last_safe[0],
            hazards.last_safe[1],
            SIDESTEP_TOLERANCE_M,
            RETREAT_TIMEOUT_SECONDS,
        )
        hazards.retreating = False
        walked["retreated_to"] = list(hazards.last_safe)
    return walked


def walk_with_sidesteps(
    steering,
    target_x: float,
    target_z: float,
    tolerance_m: float,
    timeout_seconds: float,
) -> dict:
    result = steering.go_to(target_x, target_z, tolerance_m, timeout_seconds)
    detours = 0
    while result.reason.startswith("stuck") and detours < DETOUR_ATTEMPTS:
        player = steering.position()
        ahead = GroundVector(target_x, target_z).minus(player).normalized()
        side = 1.0 if detours % 2 == 0 else -1.0
        steering.go_to(
            player.x + side * ahead.z * SIDESTEP_M,
            player.z - side * ahead.x * SIDESTEP_M,
            SIDESTEP_TOLERANCE_M,
            SIDESTEP_TIMEOUT_SECONDS,
        )
        detours += 1
        result = steering.go_to(target_x, target_z, tolerance_m, timeout_seconds)
    return {
        "arrived": result.arrived,
        "reason": result.reason,
        "remaining": result.remaining,
        "detours": detours,
    }
