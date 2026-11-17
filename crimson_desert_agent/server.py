import asyncio
import os
import tempfile
import time

from mcp.server.fastmcp import FastMCP, Image

from . import client, peer
from .development import game_lock as lock
from .development import mod_loop as jobs
from .development import peer_process as peer_lifecycle
from .development.packet_recording import read_start_actions
from .game.game_log import read_log
from .game.virtual_pad import CONTROL_NAMES
from .scripting.observation import with_camera_angles
from .scripting.script import USAGE
from .settings import GAME_DIRECTORY, GAME_LOG_PATH

server = FastMCP(
    "crimson-desert",
    instructions=(
        "Play and develop on Crimson Desert. run_script drives the player through a virtual Xbox 360 pad and "
        "reads structured state; run_peer_script drives the co-op peer body. Send whole sequences in one call: "
        "each returns every step's result and timing. Start player scripts with 'focus'. For mod development "
        "use screenshot, peer_process, mod_loop, read_game_log, start_actions and game_lock instead of "
        "hand-written shell. Load the play-crimson-desert, play-crimson-desert-peer or "
        "develop-crimson-desert-mod skill for the task at hand."
    ),
)

RUN_SCRIPT_DESCRIPTION = (
    f"Run a script of pad and observation steps in the game and return per-step results and timings. {USAGE}. "
    f"Controls: {', '.join(CONTROL_NAMES)}. Sticks are in [-1, 1]; the left stick moves relative to the camera, "
    "the right stick turns the camera. press taps one control; down, up and stick change the pad without "
    "waiting, so 'down lt; wait 0.3; press x; up lt' overlaps inputs; hold, move and look hold for SECONDS then "
    "release. turn rotates the camera to a ground heading (degrees from +Z toward +X) and goto runs to the "
    "ground point X Z while holding the listed controls, both steering in closed loop from live state. state "
    "returns position, health, velocity and the nearest actors; status adds speed, focus, pad and every actor. "
    "shot saves a JPEG of the game window: scale=1 is full resolution, crop cuts a pixel box, actor=KEY or "
    "actor=coop_copy crops around an actor, brightness lifts night scenes, burst and every join frames side "
    "by side. teach walks the player until the peer has learnt to move and animate. Everything is released "
    "when the script ends, fails or is aborted."
)
PEER_SCRIPT_DESCRIPTION = (
    "Drive the co-op peer, a second character that needs no game window, through the control port of "
    "cdmp_peer's agent mode. The script is peer commands separated by ';', one datagram each; each answer "
    f"comes back with its timing. Send 'help' first: the peer lists the commands it accepts. {peer.LOCAL_COMMANDS}"
)


@server.tool(description=RUN_SCRIPT_DESCRIPTION)
async def run_script(script: str) -> dict:
    return await asyncio.to_thread(client.run_script, script)


@server.tool(description=PEER_SCRIPT_DESCRIPTION)
async def run_peer_script(script: str) -> dict:
    return await asyncio.to_thread(peer.run_peer_script, script)


@server.tool(
    description="Stop the player script that is running now and release every control."
)
async def abort() -> dict:
    return await asyncio.to_thread(client.request, {"abort": True}, False)


@server.tool(
    description="Full game state from the mod bridge, with camera heading and pitch added."
)
def get_state() -> dict:
    with peer.open_bridge() as bridge:
        return with_camera_angles(bridge.read_state())


@server.tool(
    description=(
        "A JPEG of the game window. options are the shot step's options, such as 'scale=1', "
        "'actor=coop_copy size=600 scale=1 brightness=1.8' or 'burst=4 every=0.25'."
    )
)
async def screenshot(options: str = "") -> Image:
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "game.jpg")
        answer = await asyncio.to_thread(client.run_script, f"shot {path} {options}")
        if not answer["ok"]:
            raise RuntimeError(answer["error"])
        with open(path, "rb") as image_file:
            return Image(data=image_file.read(), format="jpeg")


@server.tool(
    description=(
        "The agent peer process: status, start (waits until the body is placed), stop or restart."
    )
)
async def peer_process(action: str) -> dict:
    if action not in peer_lifecycle.ACTIONS:
        return {"ok": False, "error": f"actions: {', '.join(peer_lifecycle.ACTIONS)}"}
    return await asyncio.to_thread(peer_lifecycle.ACTIONS[action])


@server.tool(
    description=(
        f"The mod build and launch loop as a detached job. action is one of {', '.join(jobs.JOB_ACTIONS)} or "
        "status. cycle builds, deploys cdmp.asi and relaunches until the player is in the world. Every action "
        "but build and status needs holder, the name that holds the game lock. Poll status until running is false."
    )
)
def mod_loop(action: str, holder: str = "") -> dict:
    return jobs.job_status() if action == "status" else jobs.start_job(action, holder)


@server.tool(
    description="The shared game lock: action show, take or release, with the holder's name."
)
def game_lock(action: str, holder: str = "") -> dict:
    try:
        if action == "take":
            lock.take(holder, time.strftime("%H:%M:%S"))
        elif action == "release":
            lock.release(holder)
    except lock.LockRefused as error:
        return {"ok": False, "error": str(error)}
    return {"ok": True, "holder": lock.holder()}


@server.tool(
    description=(
        "The mod log of this launch: the last lines, optionally only those matching a regular expression."
    )
)
def read_game_log(pattern: str = "", lines: int = 40) -> list[str]:
    return read_log(GAME_LOG_PATH, pattern or None, lines)


@server.tool(
    description=(
        "The player's StartAction requests in the newest packet recording, or in file: time, action hashes "
        "and position."
    )
)
def start_actions(last: int = 40, file: str = "") -> dict:
    return read_start_actions(GAME_DIRECTORY, file or None, last)


def main() -> None:
    server.run()
