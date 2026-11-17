import argparse
import json
import time

from .game.session import adopt_graphical_session
from .scripting.script import USAGE


def show(answer: dict) -> int:
    print(json.dumps(answer))
    return 0 if answer.get("ok", True) else 1


def state(_: argparse.Namespace) -> int:
    from .game.line_client import LineServiceUnavailable
    from .peer import open_bridge
    from .scripting.observation import with_camera_angles

    try:
        with open_bridge() as bridge:
            return show(with_camera_angles(bridge.read_state()))
    except LineServiceUnavailable as error:
        print(error)
        return 1


def run(arguments: argparse.Namespace) -> int:
    from .client import run_script

    return show(run_script(" ".join(arguments.script)))


def peer(arguments: argparse.Namespace) -> int:
    from .peer import run_peer_script

    return show(run_peer_script(" ".join(arguments.script)))


def peer_process(arguments: argparse.Namespace) -> int:
    from .development.peer_process import ACTIONS

    return show(ACTIONS[arguments.action]())


def mod(arguments: argparse.Namespace) -> int:
    from .development.mod_loop import job_status, start_job

    return show(
        job_status()
        if arguments.action == "status"
        else start_job(arguments.action, arguments.holder)
    )


def job(arguments: argparse.Namespace) -> int:
    from .development.mod_loop import run_job

    return run_job(arguments.action)


def lock(arguments: argparse.Namespace) -> int:
    from .development import game_lock

    try:
        if arguments.action == "take":
            game_lock.take(arguments.holder, time.strftime("%H:%M:%S"))
        elif arguments.action == "release":
            game_lock.release(arguments.holder)
    except game_lock.LockRefused as error:
        return show({"ok": False, "error": str(error)})
    return show({"ok": True, "holder": game_lock.holder()})


def log(arguments: argparse.Namespace) -> int:
    from .game.game_log import read_log
    from .settings import GAME_LOG_PATH

    print("\n".join(read_log(GAME_LOG_PATH, arguments.grep, arguments.lines)))
    return 0


def packets(arguments: argparse.Namespace) -> int:
    from .development.packet_recording import read_start_actions
    from .settings import GAME_DIRECTORY

    return show(read_start_actions(GAME_DIRECTORY, arguments.file, arguments.last))


def daemon_request(arguments: argparse.Namespace) -> int:
    from .client import DaemonUnavailable, request

    try:
        return show(request({arguments.command: True}, start_if_absent=False))
    except DaemonUnavailable as error:
        print(error)
        return 0


def serve(arguments: argparse.Namespace) -> int:
    if arguments.command == "mcp":
        from .server import main as serve_mcp

        serve_mcp()
    else:
        from .daemon import serve as serve_daemon

        serve_daemon()
    return 0


def measure(arguments: argparse.Namespace) -> int:
    from .measurement import report

    print(report(arguments.repetitions))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="crimson-desert", epilog=USAGE)
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("mcp", "daemon"):
        commands.add_parser(name).set_defaults(handler=serve)
    for name in ("abort", "quit"):
        commands.add_parser(
            name, help=f"{name} the input daemon's script"
        ).set_defaults(handler=daemon_request)
    commands.add_parser("state", help="full game state from the bridge").set_defaults(
        handler=state
    )
    for name, handler, text in (
        ("run", run, "run a player script"),
        ("peer", peer, "run a peer script"),
    ):
        command = commands.add_parser(name, help=text)
        command.add_argument("script", nargs="+")
        command.set_defaults(handler=handler)
    command = commands.add_parser(
        "peer-process", help="start, stop or restart the agent peer"
    )
    command.add_argument("action", choices=("status", "start", "stop", "restart"))
    command.set_defaults(handler=peer_process)
    command = commands.add_parser(
        "mod", help="build, deploy and relaunch as a detached job"
    )
    command.add_argument(
        "action",
        choices=("build", "launch", "relaunch", "deploy-relaunch", "cycle", "status"),
    )
    command.add_argument("--holder", help="the name holding the game lock")
    command.set_defaults(handler=mod)
    command = commands.add_parser("job")
    command.add_argument("action")
    command.set_defaults(handler=job)
    command = commands.add_parser("lock", help="the shared game lock")
    command.add_argument("action", choices=("show", "take", "release"))
    command.add_argument("holder", nargs="?", default="")
    command.set_defaults(handler=lock)
    command = commands.add_parser("log", help="the mod log of this launch")
    command.add_argument("--grep")
    command.add_argument("--lines", type=int, default=40)
    command.set_defaults(handler=log)
    command = commands.add_parser(
        "packets", help="the player's StartAction requests in a packet recording"
    )
    command.add_argument("--file")
    command.add_argument("--last", type=int, default=40)
    command.set_defaults(handler=packets)
    command = commands.add_parser("measure")
    command.add_argument("repetitions", nargs="?", type=int, default=5)
    command.set_defaults(handler=measure)
    return root


def main(arguments: list[str]) -> int:
    adopt_graphical_session()
    parsed = parser().parse_args(arguments)
    return parsed.handler(parsed)
