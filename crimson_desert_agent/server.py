import asyncio
import os
import tempfile

from mcp.server.fastmcp import FastMCP, Image

from . import client, peer
from .game import desktop
from .game.bridge_client import BridgeSession
from .game.game_log import GameLog
from .scripting.observation import with_camera_angles
from .scripting.script import USAGE
from .settings import BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT_SECONDS, GAME_LOG_PATH
from .game.virtual_pad import CONTROL_NAMES

server = FastMCP(
    "crimson-desert",
    instructions=(
        "Play Crimson Desert through a virtual Xbox 360 pad and structured state read from game memory. "
        "Send whole input sequences in one run_script call: one call runs many timed steps and returns each "
        "step's result and timing, so prefer one long script over many small calls. Start a session with "
        "'focus' as the first step, because input reaches the game only while its window has focus. "
        "Load the play-crimson-desert skill for the control map and the observe-act loop. To play the co-op "
        "peer instead of the player, use run_peer_script and the play-crimson-desert-peer skill."
    ),
)
game_log = GameLog(GAME_LOG_PATH)

RUN_SCRIPT_DESCRIPTION = (
    f"Run a script of pad and observation steps in the game and return per-step results and timings. {USAGE}. "
    f"Controls: {', '.join(CONTROL_NAMES)}. Sticks are in [-1, 1]; the left stick moves relative to the camera, "
    "the right stick turns the camera. press taps one control; down, up and stick change the pad without "
    "waiting, so 'down lt; wait 0.3; press x; up lt' overlaps inputs; hold, move and look hold for SECONDS then "
    "release. turn rotates the camera to a ground heading (degrees from +Z toward +X) and goto runs to the "
    "ground point X Z while holding the listed controls, both steering in closed loop from live state. state "
    "returns position, health and camera angles; shot saves a JPEG of the game window; log returns new mod log "
    "lines. Everything is released when the script ends, fails or is aborted."
)


@server.tool(description=RUN_SCRIPT_DESCRIPTION)
async def run_script(script: str) -> dict:
    return await asyncio.to_thread(client.run_script, script)


@server.tool(
    description=(
        "Drive the co-op peer, a second character that needs no game window, through the control port of "
        "cdmp_peer's agent mode. The script is peer commands separated by ';', sent in order, one "
        "datagram each; each answer comes back with its timing. 'wait SECONDS' pauses between commands. Send "
        "'help' first: the peer lists the commands it accepts."
    )
)
async def run_peer_script(script: str) -> dict:
    return await asyncio.to_thread(peer.run_peer_script, script)


@server.tool(
    description="Stop the script that is running now and release every control."
)
async def abort() -> dict:
    return await asyncio.to_thread(client.request, {"abort": True}, False)


@server.tool(
    description=(
        "Full game state from the mod: in_world, player position [x, y, z] in metres with Y up, rotation "
        "quaternion, health, camera position, forward and right vectors, camera heading (degrees from +Z toward "
        "+X) and pitch."
    )
)
def get_state() -> dict:
    with BridgeSession(BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT_SECONDS) as bridge:
        return with_camera_angles(bridge.read_state())


@server.tool(description="A half-resolution JPEG of the game window.")
def screenshot() -> Image:
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "game.jpg")
        desktop.screenshot(path)
        with open(path, "rb") as image_file:
            return Image(data=image_file.read(), format="jpeg")


@server.tool(
    description="Lines the mod wrote to its log since the last call, without the routine ones."
)
def read_game_log() -> list[str]:
    return game_log.new_lines()


def main() -> None:
    server.run()
