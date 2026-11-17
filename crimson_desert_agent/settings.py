import os

RUNTIME_DIRECTORY = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
SOCKET_PATH = os.path.join(RUNTIME_DIRECTORY, "crimson-desert-agent.sock")
DAEMON_LOG_PATH = os.path.join(RUNTIME_DIRECTORY, "crimson-desert-agent.log")
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = int(os.environ.get("CRIMSON_DESERT_BRIDGE_PORT", "37020"))
BRIDGE_TIMEOUT_SECONDS = 2.0
GAME_DIRECTORY = os.path.expanduser(
    os.environ.get(
        "CRIMSON_DESERT_BIN64",
        "~/.local/share/Steam/steamapps/common/Crimson Desert/bin64",
    )
)
GAME_LOG_PATH = os.path.join(GAME_DIRECTORY, "cdmp.log")
PEER_PORT = int(os.environ.get("CRIMSON_DESERT_PEER_PORT", "37021"))
PEER_TIMEOUT_SECONDS = 2.0
GAME_LOCK_PATH = os.path.expanduser(
    os.environ.get("CRIMSON_DESERT_GAME_LOCK", "~/.local/share/cdmp/game.lock")
)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD_REPOSITORY = os.path.expanduser(
    os.environ.get(
        "CRIMSON_DESERT_MOD_REPOSITORY",
        os.path.join(os.path.dirname(PLUGIN_ROOT), "CrimsonDesertMultiplayer"),
    )
)
STEAM_APPLICATION = os.environ.get("CRIMSON_DESERT_STEAM_APPLICATION", "3321460")
STEAM_CONSOLE_LOG = os.path.expanduser("~/.local/share/Steam/logs/console_log.txt")
GAME_PROCESS = "CrimsonDesert.e"
PEER_PROCESS = "cdmp_peer.exe"
JOB_LOG_PATH = os.path.join(RUNTIME_DIRECTORY, "crimson-desert-agent-job.log")
PEER_LOG_PATH = os.path.join(RUNTIME_DIRECTORY, "crimson-desert-agent-peer.log")
