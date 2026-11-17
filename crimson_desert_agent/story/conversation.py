from .acquaintances import name_in

TALK_HOLD_SECONDS = 1.0
POLL_SECONDS = 2.0
START_WITHIN_SECONDS = 8.0
DEFAULT_TIMEOUT_SECONDS = 180.0


def hold_talk(pad, pause) -> None:
    pad.set_control("x", True)
    pause(TALK_HOLD_SECONDS)
    pad.set_control("x", False)


def press_once(pad, pause) -> None:
    pad.set_control("a", True)
    pause(0.1)
    pad.set_control("a", False)


def converse(pad, read_hud, read_state, pause, clock, timeout_seconds: float) -> dict:
    before = read_hud()
    hold_talk(pad, pause)
    started_at = clock()
    started, halted, spoken, name = (
        False,
        None,
        [],
        name_in([line["text"] for line in before["other"]]),
    )
    after = before
    while clock() - started_at < timeout_seconds:
        pause(POLL_SECONDS)
        after = read_hud()
        texts = after["speech"] + [line["text"] for line in after["other"]]
        name = name or name_in(texts)
        spoken += [text for text in after["speech"] if text not in spoken]
        if after["exit_prompt"]:
            halted = "exit"
            break
        if (
            read_state().get("paused")
            and after["quest"] is None
            and not after["speech"]
        ):
            halted = "tutorial"
            break
        in_conversation = after["quest"] is None or bool(after["speech"])
        started = started or in_conversation
        if started and not in_conversation:
            break
        if not started and clock() - started_at > START_WITHIN_SECONDS:
            break
        if after["prompt"] and after["prompt"]["action"] == "Next":
            press_once(pad, pause)
    return {
        "started": started,
        "halted": halted,
        "name": name,
        "spoken": spoken,
        "quest_before": [before["quest"], *before["objectives"]],
        "quest_after": [after["quest"], *after["objectives"]],
        "guide_before": before["guide"],
        "guide_after": after["guide"],
        "seconds": round(clock() - started_at, 1),
    }
