TICK_SECONDS = 0.25
PRESS_IN_SECONDS = 0.6
JUMP_EVERY_SECONDS = 5.5
MAXIMUM_JUMPS = 2
TOP_GAIN_M = 0.3


def jump(pad, pause) -> None:
    pad.set_control("x", True)
    pause(0.15)
    pad.set_control("x", False)


def climb(pad, read_state, pause, clock, seconds: float) -> dict:
    start_height = best = read_state()["player"]["position"][1]
    heights = []
    pad.set_left_stick(0.0, 1.0)
    try:
        pause(PRESS_IN_SECONDS)
        jump(pad, pause)
        started = clock()
        jumps, last_jump = 1, clock()
        while clock() - started < seconds:
            pause(TICK_SECONDS)
            now_height = read_state()["player"]["position"][1]
            best = max(best, now_height)
            if len(heights) < int(clock() - started):
                heights.append(round(now_height - start_height, 1))
            if jumps < MAXIMUM_JUMPS and clock() - last_jump >= JUMP_EVERY_SECONDS:
                jump(pad, pause)
                jumps, last_jump = jumps + 1, clock()
    finally:
        pad.set_left_stick(0.0, 0.0)
    height = read_state()["player"]["position"][1]
    return {
        "climbed_m": round(height - start_height, 1),
        "peak_m": round(best - start_height, 1),
        "gain_each_second": heights,
        "on_top": height >= best - TOP_GAIN_M and best - start_height > 1.0,
    }
