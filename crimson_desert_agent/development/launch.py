import os
import subprocess
import time
from typing import Callable

from .. import client
from ..game import pointer
from ..game.bridge_client import BridgeSession
from ..game.line_client import LineServiceUnavailable
from ..settings import (
    BRIDGE_HOST,
    BRIDGE_PORT,
    BRIDGE_TIMEOUT_SECONDS,
    GAME_LOG_PATH,
    GAME_PROCESS,
    STEAM_APPLICATION,
    STEAM_CONSOLE_LOG,
)
from . import processes

SHADER_DIALOG_SKIP_POINT = tuple(
    int(part)
    for part in os.environ.get(
        "CRIMSON_DESERT_SHADER_DIALOG_SKIP_POINT", "970 591"
    ).split()
)
WORLD_TIMEOUT_SECONDS = float(
    os.environ.get("CRIMSON_DESERT_WORLD_TIMEOUT_SECONDS", "900")
)
GAME_UP_LINE = "Late init: game is up"


class LaunchFailed(Exception):
    pass


def in_world() -> bool:
    try:
        with BridgeSession(BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT_SECONDS) as bridge:
            return bool(bridge.read_state().get("in_world"))
    except LineServiceUnavailable:
        return False


def steam_says(*words: str) -> str | None:
    try:
        with open(STEAM_CONSOLE_LOG, errors="replace") as log_file:
            tail = log_file.readlines()[-2:]
    except OSError:
        return None
    return next((word for word in words if any(word in line for line in tail)), None)


def log_has(text: str) -> bool:
    try:
        with open(GAME_LOG_PATH, errors="replace") as log_file:
            return text in log_file.read()
    except OSError:
        return False


def rotate_log() -> None:
    if os.path.exists(GAME_LOG_PATH):
        os.replace(GAME_LOG_PATH, GAME_LOG_PATH.removesuffix(".log") + ".previous.log")


def start_game(say: Callable[[str], None]) -> None:
    if client.daemon_answers():
        client.request({"quit": True}, start_if_absent=False)
    subprocess.Popen(
        ["steam", f"steam://rungameid/{STEAM_APPLICATION}"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(30):
        if processes.is_running(GAME_PROCESS) or steam_says(
            "ProcessingShaderCa", "Failed"
        ):
            break
        time.sleep(2)
    if steam_says("Failed"):
        raise LaunchFailed("Steam reported that the launch failed")
    if steam_says("ProcessingShaderCa"):
        say("skipping the shader cache dialog")
        pointer.click(*SHADER_DIALOG_SKIP_POINT)


def wait_for_world(say: Callable[[str], None]) -> None:
    deadline = time.monotonic() + WORLD_TIMEOUT_SECONDS
    announced_up = False
    while time.monotonic() < deadline:
        if in_world():
            say("in world")
            return
        if log_has(GAME_UP_LINE):
            if not announced_up:
                say("game is up, pressing through the title")
                announced_up = True
            client.run_script("focus; press a 0.1 0.1")
        elif not processes.is_running(GAME_PROCESS) and not steam_says(
            "ProcessingShaderCa"
        ):
            time.sleep(10)
            if not processes.is_running(GAME_PROCESS):
                raise LaunchFailed("the game process is not running")
        time.sleep(5)
    raise LaunchFailed(f"the world did not load within {WORLD_TIMEOUT_SECONDS:g} s")


def launch(
    say: Callable[[str], None],
    restart: bool,
    before_start: Callable[[], None] = lambda: None,
) -> None:
    if restart:
        say("stopping the game")
        if not processes.stop(GAME_PROCESS):
            raise LaunchFailed("the game did not stop")
    if not processes.is_running(GAME_PROCESS):
        rotate_log()
        before_start()
        say("starting the game through Steam")
        start_game(say)
    wait_for_world(say)
