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
