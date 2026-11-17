import os
import shutil
import subprocess
import sys
import time

from ..settings import GAME_DIRECTORY, JOB_LOG_PATH, MOD_REPOSITORY, PLUGIN_ROOT
from . import game_lock, processes
from .launch import LaunchFailed, launch

JOB_ACTIONS = ("build", "relaunch", "deploy-relaunch", "cycle", "launch")
OUTCOME_PREFIX = "JOB "


def say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


def build() -> None:
    say("building the mod")
    completed = subprocess.run(
        ["nice", "-n", "19", os.path.join(MOD_REPOSITORY, "scripts", "build-linux.sh")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in completed.stdout.splitlines()[-15:]:
        say(line)
    if completed.returncode != 0:
        raise LaunchFailed(f"the build failed with exit code {completed.returncode}")


def deploy() -> None:
    built = os.path.join(MOD_REPOSITORY, "build", "linux", "bin", "cdmp.asi")
    say(f"deploying {built}")
    shutil.copy2(built, os.path.join(GAME_DIRECTORY, "cdmp.asi"))


def run_job(action: str) -> int:
    try:
        if action in ("build", "cycle"):
            build()
        if action == "launch":
            launch(say, restart=False)
        if action == "relaunch":
            launch(say, restart=True)
        if action in ("deploy-relaunch", "cycle"):
            launch(say, restart=True, before_start=deploy)
    except (LaunchFailed, OSError) as error:
        say(f"{OUTCOME_PREFIX}failed: {action}: {error}")
        return 1
    say(f"{OUTCOME_PREFIX}done: {action}")
    return 0


def job_status() -> dict:
    try:
        with open(JOB_LOG_PATH, errors="replace") as log_file:
            lines = [line.rstrip() for line in log_file.readlines()]
    except OSError:
        return {"ok": True, "running": False, "lines": []}
    outcome = next((line for line in reversed(lines) if OUTCOME_PREFIX in line), None)
    return {
        "ok": True,
        "running": outcome is None,
        "outcome": outcome,
        "lines": lines[-12:],
    }


def start_job(action: str, holder: str | None) -> dict:
    if action not in JOB_ACTIONS:
        return {
            "ok": False,
            "error": f"unknown action {action!r}; actions: {', '.join(JOB_ACTIONS)}, status",
        }
    try:
        if action != "build":
            game_lock.require(holder)
    except game_lock.LockRefused as error:
        return {"ok": False, "error": str(error)}
    if job_status()["running"] and os.path.exists(JOB_LOG_PATH):
        return {
            "ok": False,
            "error": "a job is still running; read it with action status",
        }
    open(JOB_LOG_PATH, "w").close()
    processes.start_detached(
        [sys.executable, "-m", "crimson_desert_agent", "job", action],
        JOB_LOG_PATH,
        cwd=PLUGIN_ROOT,
    )
    return {
        "ok": True,
        "started": action,
        "log": JOB_LOG_PATH,
        "next": "poll with action status until running is false",
    }
