import os
import time
from typing import Callable

from .. import client
from ..game import pointer
from ..game.bridge_client import BridgeSession
from ..game.desktop import hyprland
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
PROCESS_START_GRACE_SECONDS = 120.0
STEAM_START_SECONDS = 180.0


class LaunchFailed(Exception):
    pass


def in_world() -> bool:
    try:
        with BridgeSession(BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT_SECONDS) as bridge:
            return bool(bridge.read_state().get("in_world"))
    except LineServiceUnavailable:
        return False


def steam_launch_step() -> str:
    try:
        with open(STEAM_CONSOLE_LOG, errors="replace") as log_file:
            steps = [
                line
                for line in log_file.readlines()[-400:]
                if "LaunchApp" in line or "launch failed" in line.lower()
            ]
    except OSError:
        return ""
    return steps[-1] if steps else ""


def waiting_on_shader_dialog() -> bool:
    return "waiting for user response to ProcessingShaderCache" in steam_launch_step()


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
    hyprland(f"dispatch exec steam steam://rungameid/{STEAM_APPLICATION}")
    deadline = time.monotonic() + STEAM_START_SECONDS
    while time.monotonic() < deadline and not processes.is_running(GAME_PROCESS):
        if "failed" in steam_launch_step().lower():
            raise LaunchFailed(f"Steam reported: {steam_launch_step().strip()}")
        if waiting_on_shader_dialog():
            say("skipping the shader cache dialog")
            pointer.click(*SHADER_DIALOG_SKIP_POINT)
        time.sleep(3)


def wait_for_world(say: Callable[[str], None]) -> None:
    deadline = time.monotonic() + WORLD_TIMEOUT_SECONDS
    process_last_seen = time.monotonic()
    announced_up = False
    while time.monotonic() < deadline:
        if in_world():
            say("in world")
            return
        if processes.is_running(GAME_PROCESS):
            process_last_seen = time.monotonic()
        elif time.monotonic() - process_last_seen > PROCESS_START_GRACE_SECONDS:
            raise LaunchFailed(f"no game process for {PROCESS_START_GRACE_SECONDS:g} s")
        if log_has(GAME_UP_LINE):
            if not announced_up:
                say("game is up, pressing through the title")
                announced_up = True
            client.run_script("focus; press a 0.1 0.1")
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
