from typing import Callable

WALK_SECONDS = 0.8
REST_SECONDS = 0.5
DEFAULT_TIMEOUT_SECONDS = 20.0
LESSONS = ("has_move_template", "knows_walk_animation")


def learnt(peer_state: dict) -> dict:
    return {lesson: bool(peer_state.get(lesson, True)) for lesson in LESSONS}


def teach_peer(
    pad,
    ask_peer: Callable[[str], dict],
    pause: Callable[[float], None],
    clock: Callable[[], float],
    timeout_seconds: float,
) -> dict:
    started = clock()
    forward = 1.0
    lessons = learnt(ask_peer("state"))
    while not all(lessons.values()) and clock() - started < timeout_seconds:
        pad.set_left_stick(0.0, forward)
        pause(WALK_SECONDS)
        pad.set_left_stick(0.0, 0.0)
        pause(REST_SECONDS)
        forward = -forward
        lessons = learnt(ask_peer("state"))
    return {
        "taught": all(lessons.values()),
        **lessons,
        "elapsed_seconds": round(clock() - started, 2),
    }
