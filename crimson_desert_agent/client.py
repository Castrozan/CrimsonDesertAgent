import json
import os
import socket
import subprocess
import sys
import time

from .settings import DAEMON_LOG_PATH, SOCKET_PATH

DAEMON_START_SECONDS = 10.0
PACKAGE_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DaemonUnavailable(Exception):
    pass


def connect() -> socket.socket:
    connection = socket.socket(socket.AF_UNIX)
    try:
        connection.connect(SOCKET_PATH)
    except OSError:
        connection.close()
        raise
    return connection


def daemon_answers() -> bool:
    try:
        connect().close()
    except OSError:
        return False
    return True


def start_daemon() -> socket.socket:
    with open(DAEMON_LOG_PATH, "ab") as log_file:
        subprocess.Popen(
            [sys.executable, "-m", "crimson_desert_agent", "daemon"],
            cwd=PACKAGE_PARENT,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )
    deadline = time.monotonic() + DAEMON_START_SECONDS
    while time.monotonic() < deadline:
        try:
            return connect()
        except OSError:
            time.sleep(0.05)
    raise DaemonUnavailable(f"the input daemon did not start; see {DAEMON_LOG_PATH}")


def request(payload: dict, start_if_absent: bool = True) -> dict:
    started = time.perf_counter()
    try:
        connection = connect()
    except OSError as error:
        if not start_if_absent:
            raise DaemonUnavailable("the input daemon is not running") from error
        connection = start_daemon()
    with connection:
        connection.sendall(json.dumps(payload).encode() + b"\n")
        line = connection.makefile("r", encoding="utf-8").readline()
    if not line:
        raise DaemonUnavailable(
            f"the input daemon closed the connection; see {DAEMON_LOG_PATH}"
        )
    answer = json.loads(line)
    answer["round_trip_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return answer


def run_script(script: str) -> dict:
    return request({"script": script})
