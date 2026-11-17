import json
import sys

from .scripting.script import USAGE

COMMANDS = "mcp | daemon | state | run SCRIPT | abort | quit | measure [REPETITIONS]"


def main(arguments: list[str]) -> int:
    command = arguments[0] if arguments else ""
    if command == "mcp":
        from .server import main as serve_mcp

        serve_mcp()
    elif command == "daemon":
        from .daemon import serve

        serve()
    elif command == "run" and len(arguments) > 1:
        from .client import run_script

        answer = run_script(" ".join(arguments[1:]))
        print(json.dumps(answer))
        return 0 if answer["ok"] else 1
    elif command in ("abort", "quit"):
        from .client import DaemonUnavailable, request

        try:
            print(json.dumps(request({command: True}, start_if_absent=False)))
        except DaemonUnavailable as error:
            print(error)
    elif command == "state":
        from .game.bridge_client import BridgeSession, BridgeUnavailable
        from .scripting.observation import with_camera_angles
        from .settings import BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT_SECONDS

        try:
            with BridgeSession(BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT_SECONDS) as bridge:
                print(json.dumps(with_camera_angles(bridge.read_state())))
        except BridgeUnavailable as error:
            print(error)
            return 1
    elif command == "measure":
        from .measurement import report

        print(report(int(arguments[1]) if len(arguments) > 1 else 5))
    else:
        print(f"usage: {COMMANDS}\n{USAGE}")
        return 2
    return 0


sys.exit(main(sys.argv[1:]))
