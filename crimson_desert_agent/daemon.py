import json
import os
import socket
import socketserver
import threading
import time

from .game import desktop
from .game.bridge_client import BridgeSession
from .scripting.engine import Engine
from .game.game_log import GameLog
from .settings import (
    BRIDGE_HOST,
    BRIDGE_PORT,
    BRIDGE_TIMEOUT_SECONDS,
    GAME_LOG_PATH,
    SOCKET_PATH,
)
from .game.virtual_pad import VirtualPad


class Daemon:
    def __init__(self) -> None:
        self._abort = threading.Event()
        self._running = threading.Lock()
        self._engine: Engine | None = None
        self._pad: VirtualPad | None = None

    def start(self) -> None:
        self._pad = VirtualPad()
        self._engine = Engine(
            self._pad,
            lambda: BridgeSession(BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT_SECONDS),
            desktop,
            GameLog(GAME_LOG_PATH),
            self._abort.wait,
            time.monotonic,
        )

    def stop(self) -> None:
        self._abort.set()
        with self._running:
            if self._pad is not None:
                self._pad.close()

    def answer(self, request: dict) -> dict:
        if request.get("abort"):
            self._abort.set()
            return {"ok": True}
        if "script" not in request:
            return {
                "ok": False,
                "error": 'send {"script": "..."}, {"abort": true} or {"quit": true}',
            }
        with self._running:
            self._abort.clear()
            return self._engine.run(request["script"])


class ThreadedUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


def another_daemon_answers() -> bool:
    try:
        with socket.socket(socket.AF_UNIX) as probe:
            probe.connect(SOCKET_PATH)
        return True
    except OSError:
        return False


def serve() -> None:
    if another_daemon_answers():
        return
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    daemon = Daemon()

    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            line = self.rfile.readline()
            if not line.strip():
                return
            request = json.loads(line)
            if request.get("quit"):
                self.wfile.write(b'{"ok": true}\n')
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            self.wfile.write(json.dumps(daemon.answer(request)).encode() + b"\n")

    with ThreadedUnixServer(SOCKET_PATH, Handler) as server:
        daemon.start()
        try:
            server.serve_forever()
        finally:
            daemon.stop()
            os.unlink(SOCKET_PATH)
