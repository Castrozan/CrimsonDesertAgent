TICK_SECONDS = 0.25
REST_SECONDS = 12.0
SECOND_JUMP_AFTER_SECONDS = 5.5
TOP_GAIN_M = 0.3


def jump(pad, pause) -> None:
    pad.set_control("x", True)
    pause(0.15)
    pad.set_control("x", False)


def climb(pad, read_state, pause, clock, seconds: float) -> dict:
    pause(REST_SECONDS)
    start_height = best = read_state()["player"]["position"][1]
    pad.set_left_stick(0.0, 1.0)
    try:
        jump(pad, pause)
        started = clock()
        jumped_again = False
        while clock() - started < seconds:
            pause(TICK_SECONDS)
            best = max(best, read_state()["player"]["position"][1])
            if not jumped_again and clock() - started >= SECOND_JUMP_AFTER_SECONDS:
                jump(pad, pause)
                jumped_again = True
    finally:
        pad.set_left_stick(0.0, 0.0)
    height = read_state()["player"]["position"][1]
    return {
        "climbed_m": round(height - start_height, 1),
        "peak_m": round(best - start_height, 1),
        "on_top": height >= best - TOP_GAIN_M and best - start_height > 1.0,
    }
