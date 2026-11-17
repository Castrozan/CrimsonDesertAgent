IDLE_WINDOW_SECONDS = 30.0
FLUSH_POLL_SECONDS = 1.0
DEFAULT_FLUSH_SECONDS = 8.0
RECENT_ACTIONS = 400


def hashes(action: dict) -> tuple[str, str]:
    return (action["first_hash"], action["second_hash"])


def prove(pad, control: str, read_start_actions, pause, flush_seconds: float) -> dict:
    recorded = read_start_actions(RECENT_ACTIONS)
    if not recorded.get("ok"):
        return {"proven": False, "reason": recorded.get("error")}
    actions = recorded["start_actions"]
    latest = actions[-1]["seconds"] if actions else 0.0
    idle = {
        hashes(action)
        for action in actions
        if action["seconds"] >= latest - IDLE_WINDOW_SECONDS
    }
    pad.set_control(control, True)
    pause(0.1)
    pad.set_control(control, False)
    fresh: list[dict] = []
    waited = 0.0
    while waited < flush_seconds and not fresh:
        pause(FLUSH_POLL_SECONDS)
        waited += FLUSH_POLL_SECONDS
        fresh = [
            action
            for action in read_start_actions(RECENT_ACTIONS).get("start_actions", [])
            if action["seconds"] > latest and hashes(action) not in idle
        ]
    return {
        "proven": bool(fresh),
        "reason": None
        if fresh
        else f"no new action hashes within {flush_seconds:g} s of pressing {control}",
        "new_actions": fresh[:6],
        "idle_hashes": sorted(first for first, _ in idle),
    }
