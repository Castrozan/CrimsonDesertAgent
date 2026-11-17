from typing import Callable

from ..game.desktop import DesktopError
from ..game.line_client import LineServiceUnavailable
from .devices import Devices
from .photography import ActorNotInView
from .script import ScriptError, parse
from .script_run import Aborted, ScriptRun


class Engine:
    def __init__(
        self,
        devices: Devices,
        wait: Callable[[float], bool],
        clock: Callable[[], float],
    ) -> None:
        self._devices = devices
        self._wait = wait
        self._clock = clock

    def run(self, script: str) -> dict:
        try:
            steps = parse(script)
        except ScriptError as error:
            return {"ok": False, "error": str(error), "steps": []}
        started = self._clock()
        reports = []
        outcome: dict = {"ok": True}
        with self._devices.open_bridge() as bridge:
            run = ScriptRun(self._devices, bridge, self._wait, self._clock)
            try:
                for step in steps:
                    step_started = self._clock()
                    report: dict = {"step": step.text}
                    reports.append(report)
                    result = run.execute(step)
                    report["ms"] = round((self._clock() - step_started) * 1000, 1)
                    if result is not None:
                        report["result"] = result
            except (
                Aborted,
                LineServiceUnavailable,
                DesktopError,
                ActorNotInView,
            ) as error:
                outcome = {"ok": False, "error": f"{reports[-1]['step']}: {error}"}
            finally:
                self._devices.pad.release_all()
        return {
            **outcome,
            "elapsed_ms": round((self._clock() - started) * 1000, 1),
            "steps": reports,
        }
