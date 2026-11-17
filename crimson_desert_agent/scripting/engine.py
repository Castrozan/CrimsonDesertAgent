from typing import Callable, ContextManager

from ..game.bridge_client import BridgeUnavailable
from ..game.desktop import DesktopError
from .script import ScriptError, parse
from .script_run import Aborted, ScriptRun


class Engine:
    def __init__(
        self,
        pad,
        open_bridge: Callable[[], ContextManager],
        desktop,
        game_log,
        interrupted_within: Callable[[float], bool],
        clock: Callable[[], float],
    ) -> None:
        self._pad = pad
        self._open_bridge = open_bridge
        self._desktop = desktop
        self._game_log = game_log
        self._interrupted_within = interrupted_within
        self._clock = clock

    def run(self, script: str) -> dict:
        try:
            steps = parse(script)
        except ScriptError as error:
            return {"ok": False, "error": str(error), "steps": []}
        started = self._clock()
        reports = []
        outcome: dict = {"ok": True}
        with self._open_bridge() as bridge:
            run = ScriptRun(
                self._pad,
                bridge,
                self._desktop,
                self._game_log,
                self._interrupted_within,
                self._clock,
            )
            try:
                for step in steps:
                    step_started = self._clock()
                    report: dict = {"step": step.text}
                    reports.append(report)
                    result = run.execute(step)
                    report["ms"] = round((self._clock() - step_started) * 1000, 1)
                    if result is not None:
                        report["result"] = result
            except (Aborted, BridgeUnavailable, DesktopError) as error:
                outcome = {"ok": False, "error": f"{reports[-1]['step']}: {error}"}
            finally:
                self._pad.release_all()
        return {
            **outcome,
            "elapsed_ms": round((self._clock() - started) * 1000, 1),
            "steps": reports,
        }
