import os
import time

from ..game.line_client import LineServiceUnavailable
from ..peer import open_peer
from ..settings import MOD_REPOSITORY, PEER_LOG_PATH, PEER_PROCESS
from . import processes

PEER_ARGUMENTS = ("--mode", "agent", "--delay", "50", "--offset", "0")
PLACED_TIMEOUT_SECONDS = 90.0


def peer_state() -> dict | None:
    try:
        with open_peer() as peer:
            return peer.ask("state")
    except LineServiceUnavailable:
        return None


def status() -> dict:
    return {
        "ok": True,
        "running": processes.is_running(PEER_PROCESS),
        "state": peer_state(),
    }


def stop() -> dict:
    return {
        "ok": processes.stop(PEER_PROCESS),
        "running": processes.is_running(PEER_PROCESS),
    }


def start() -> dict:
    script = os.path.join(MOD_REPOSITORY, "scripts", "peer-linux.sh")
    if not os.path.exists(script):
        return {
            "ok": False,
            "error": f"{script} not found; set CRIMSON_DESERT_MOD_REPOSITORY",
        }
    if not processes.is_running(PEER_PROCESS):
        processes.start_detached([script, *PEER_ARGUMENTS], PEER_LOG_PATH)
    deadline = time.monotonic() + PLACED_TIMEOUT_SECONDS
    state = None
    while time.monotonic() < deadline:
        state = peer_state()
        if state and state.get("placed"):
            return {"ok": True, "running": True, "state": state}
        time.sleep(1.0)
    return {
        "ok": False,
        "error": f"the peer did not report placed within {PLACED_TIMEOUT_SECONDS:g} s; "
        f"it is placed once the game connects to it. See {PEER_LOG_PATH}",
        "state": state,
    }


def restart() -> dict:
    stopped = stop()
    return (
        start()
        if stopped["ok"]
        else {"ok": False, "error": "the peer process did not stop"}
    )


ACTIONS = {"status": status, "start": start, "stop": stop, "restart": restart}
