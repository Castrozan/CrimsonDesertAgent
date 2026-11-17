import time
from typing import Callable

from .game.bridge_client import BridgeSession
from .game.datagram_client import DatagramSession
from .game.line_client import LineServiceUnavailable
from .scripting.staging import NothingToStageAgainst, copy_error, stage_across_view
from .settings import (
    BRIDGE_HOST,
    BRIDGE_PORT,
    BRIDGE_TIMEOUT_SECONDS,
    PEER_PORT,
    PEER_TIMEOUT_SECONDS,
)

MAXIMUM_WAIT_SECONDS = 120.0
STAGE_USAGE = (
    "stage ahead=METRES from=METRES_RIGHT to=METRES_RIGHT [speed=METRES_PER_SECOND]"
)
LOCAL_COMMANDS = (
    "Handled by the plugin, not sent to the peer: 'wait SECONDS'; "
    f"'{STAGE_USAGE}' places the body ahead of the player's camera and walks it across the view; "
    "'compare' reports how far the peer body is from the copy the player's game shows."
)


class BadPeerStep(ValueError):
    pass


def open_peer() -> DatagramSession:
    return DatagramSession(
        "the peer control port", BRIDGE_HOST, PEER_PORT, PEER_TIMEOUT_SECONDS
    )


def open_bridge() -> BridgeSession:
    return BridgeSession(BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT_SECONDS)


def wait_seconds(command: str) -> float | None:
    words = command.split()
    if len(words) != 2 or words[0] != "wait":
        return None
    try:
        seconds = float(words[1])
    except ValueError:
        return None
    return seconds if 0.0 <= seconds <= MAXIMUM_WAIT_SECONDS else None


def stage(
    words: list[str], ask: Callable[[str], dict], read_state: Callable[[], dict]
) -> dict:
    try:
        options = {
            name: float(value) for name, value in (word.split("=", 1) for word in words)
        }
        ahead, start, end = options.pop("ahead"), options.pop("from"), options.pop("to")
        speed = options.pop("speed", None)
        if options:
            raise KeyError(next(iter(options)))
    except (ValueError, KeyError) as error:
        raise BadPeerStep(f"bad stage step ({error}). Usage: {STAGE_USAGE}") from error
    staged = stage_across_view(read_state(), ahead, start, end)
    answers = [ask("teleport {} {} {}".format(*staged.start))]
    if speed is not None:
        answers.append(ask(f"speed {speed}"))
    answers.append(ask("goto {} {}".format(*staged.end)))
    refused = [answer for answer in answers if not answer.get("ok", True)]
    return {
        "ok": not refused,
        "start": list(staged.start),
        "end": list(staged.end),
        **({"refused": refused} if refused else {}),
    }


def run_peer_script(
    script: str,
    open_session=open_peer,
    open_state=open_bridge,
    clock=time.monotonic,
    sleep=time.sleep,
) -> dict:
    commands = [
        text.strip() for text in script.replace("\n", ";").split(";") if text.strip()
    ]
    if not commands:
        return {
            "ok": False,
            "error": "empty script: send peer commands separated by ';', such as 'help'",
            "steps": [],
        }
    started = clock()
    reports = []
    outcome: dict = {"ok": True}
    with open_session() as session, open_state() as bridge:
        for command in commands:
            step_started = clock()
            report: dict = {"step": command}
            reports.append(report)
            words = command.split()
            seconds = wait_seconds(command)
            try:
                if seconds is not None:
                    sleep(seconds)
                elif words[0] == "stage":
                    report["result"] = stage(words[1:], session.ask, bridge.read_state)
                elif command == "compare":
                    report["result"] = copy_error(
                        session.ask("state"), bridge.read_state()
                    )
                else:
                    report["result"] = session.ask(command)
            except (
                LineServiceUnavailable,
                BadPeerStep,
                NothingToStageAgainst,
            ) as error:
                outcome = {"ok": False, "error": f"{command}: {error}"}
                break
            report["ms"] = round((clock() - step_started) * 1000, 1)
    return {
        **outcome,
        "elapsed_ms": round((clock() - started) * 1000, 1),
        "steps": reports,
    }
