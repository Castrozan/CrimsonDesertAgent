import math

from ..scripting.navigation import GroundVector, stick_toward

TICK_SECONDS = 0.1
THREAT_RANGE_M = 6.0
GUARD_RANGE_M = 4.5
STRIKE_RANGE_M = 2.3
STRIKE_EVERY_SECONDS = 1.1
QUIET_BEFORE_STRIKE_SECONDS = 0.4
GUARD_AFTER_HIT_SECONDS = 0.8
COMBO_STRIKES = 3
STRIKE_LUNGE_M = 2.5
RETURN_TIMEOUT_SECONDS = 6.0


def threats(state: dict) -> list[dict]:
    return sorted(
        (
            actor
            for actor in state.get("actors") or []
            if actor.get("kind") == "character"
            and actor.get("distance", 99.0) <= THREAT_RANGE_M
        ),
        key=lambda actor: actor["distance"],
    )


def tap(pad, control: str, pause, seconds: float) -> None:
    pad.set_control(control, True)
    pause(seconds)
    pad.set_control(control, False)


def hold_ground(
    pad,
    read_state,
    walk,
    hazards,
    pause,
    clock,
    anchor: tuple[float, float],
    seconds: float,
    leash_m: float,
) -> dict:
    started = clock()
    last_strike = last_damage = started - 10.0
    tally = {
        "strikes": 0,
        "damage_taken": 0.0,
        "returns_to_anchor": 0,
        "strikes_withheld_near_fire": 0,
    }
    health, ended = None, "time"
    try:
        while clock() - started < seconds:
            state = read_state()
            player = state.get("player")
            if not player:
                ended = "not in world"
                break
            if health is not None and player["health"] < health:
                tally["damage_taken"] += health - player["health"]
                last_damage = clock()
            health = player["health"]
            if health <= 0:
                ended = "died"
                break
            here = GroundVector.from_world(player["position"])
            if math.hypot(here.x - anchor[0], here.z - anchor[1]) > leash_m:
                pad.set_control("lb", False)
                walk(anchor[0], anchor[1], 1.0, RETURN_TIMEOUT_SECONDS)
                tally["returns_to_anchor"] += 1
                continue
            near = threats(state)
            if (
                not near
                or near[0]["distance"] > GUARD_RANGE_M
                or not state.get("camera")
            ):
                pad.set_control("lb", False)
                pause(TICK_SECONDS)
                continue
            target = GroundVector.from_world(near[0]["position"])
            now = clock()
            pad.set_control("lb", now - last_damage < GUARD_AFTER_HIT_SECONDS)
            reach = target.minus(here)
            camera = state["camera"]
            if near[0]["distance"] > STRIKE_RANGE_M and reach.length() > 0:
                closing = stick_toward(
                    here,
                    target,
                    GroundVector.from_world(camera["forward"]),
                    GroundVector.from_world(camera["right"]),
                    1.0,
                    1.0,
                )
                ahead = reach.normalized()
                if hazards.near(here.x + ahead.x * 2.0, here.z + ahead.z * 2.0):
                    pad.set_left_stick(0.0, 0.0)
                else:
                    pad.set_left_stick(closing.right, closing.forward)
            elif (
                now - last_strike >= STRIKE_EVERY_SECONDS
                and now - last_damage >= QUIET_BEFORE_STRIKE_SECONDS
                and reach.length() > 0
            ):
                pad.set_left_stick(0.0, 0.0)
                ahead = reach.normalized()
                if hazards.near(
                    here.x + ahead.x * STRIKE_LUNGE_M, here.z + ahead.z * STRIKE_LUNGE_M
                ):
                    tally["strikes_withheld_near_fire"] += 1
                else:
                    pad.set_control("lb", False)
                    for _ in range(COMBO_STRIKES):
                        tap(pad, "rb", pause, 0.08)
                        pause(0.22)
                    tally["strikes"] += COMBO_STRIKES
                last_strike = now
            else:
                pad.set_left_stick(0.0, 0.0)
            pause(TICK_SECONDS)
    finally:
        pad.set_control("lb", False)
        pad.set_left_stick(0.0, 0.0)
    return {
        "ended": ended,
        "seconds": round(clock() - started, 1),
        "health": health,
        **tally,
        "damage_taken": round(tally["damage_taken"], 1),
    }
