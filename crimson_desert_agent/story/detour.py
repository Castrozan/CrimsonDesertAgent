from ..scripting.navigation import GroundVector

SIDESTEP_M = 4.0
SIDESTEP_TIMEOUT_SECONDS = 5.0
SIDESTEP_TOLERANCE_M = 1.0
DETOUR_ATTEMPTS = 3


def go_around(
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
