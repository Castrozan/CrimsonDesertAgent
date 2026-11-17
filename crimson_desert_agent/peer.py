import time

from .game.line_client import LineServiceUnavailable, LineSession
from .settings import BRIDGE_HOST, PEER_PORT, PEER_TIMEOUT_SECONDS

MAXIMUM_WAIT_SECONDS = 120.0


def open_peer() -> LineSession:
    return LineSession("the peer control port", BRIDGE_HOST, PEER_PORT, PEER_TIMEOUT_SECONDS)


def wait_seconds(command: str) -> float | None:
    words = command.split()
    if len(words) != 2 or words[0] != "wait":
        return None
    try:
        seconds = float(words[1])
    except ValueError:
        return None
    return seconds if 0.0 <= seconds <= MAXIMUM_WAIT_SECONDS else None


def run_peer_script(script: str, open_session=open_peer, clock=time.monotonic, sleep=time.sleep) -> dict:
    commands = [text.strip() for text in script.replace("\n", ";").split(";") if text.strip()]
    if not commands:
        return {"ok": False, "error": "empty script: send peer commands separated by ';', such as 'help'", "steps": []}
    started = clock()
    reports = []
    outcome: dict = {"ok": True}
    with open_session() as session:
        for command in commands:
            step_started = clock()
            report: dict = {"step": command}
            reports.append(report)
            seconds = wait_seconds(command)
            try:
                if seconds is None:
                    report["result"] = session.ask(command)
                else:
                    sleep(seconds)
            except LineServiceUnavailable as error:
                outcome = {"ok": False, "error": f"{command}: {error}"}
                break
            report["ms"] = round((clock() - step_started) * 1000, 1)
    return {**outcome, "elapsed_ms": round((clock() - started) * 1000, 1), "steps": reports}
