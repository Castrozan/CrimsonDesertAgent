CONFIRMING_CONTROLS = frozenset({"a", "start"})


class ConfirmRefused(Exception):
    pass


def refuse_blind_confirm(names: tuple, seen: dict | None, read_state) -> bool:
    if not CONFIRMING_CONTROLS.intersection(names):
        return False
    if seen and seen["exit_prompt"]:
        raise ConfirmRefused(
            "the screen shows an exit prompt; press b to cancel it, then read hud"
        )
    if read_state().get("paused") and seen is None:
        raise ConfirmRefused(
            "the game is paused by a menu or tutorial; read hud in this script before confirming"
        )
    return True
