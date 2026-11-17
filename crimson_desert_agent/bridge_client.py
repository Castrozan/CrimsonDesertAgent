import json
import socket


class BridgeUnavailable(Exception):
    pass


class BridgeSession:
    def __init__(self, host: str, port: int, timeout_seconds: float) -> None:
        self._address = (host, port)
        self._timeout_seconds = timeout_seconds
        self._connection: socket.socket | None = None
        self._stream = None

    def __enter__(self) -> "BridgeSession":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        self._stream = None

    def read_state(self) -> dict:
        try:
            if self._connection is None:
                self._connection = socket.create_connection(
                    self._address, timeout=self._timeout_seconds
                )
                self._connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self._stream = self._connection.makefile("r", encoding="utf-8")
            self._connection.sendall(b"state\n")
            line = self._stream.readline()
        except OSError as error:
            self.close()
            raise BridgeUnavailable(
                f"game state bridge not reachable on {self._address[0]}:{self._address[1]} ({error}); "
                "is the game running with a cdmp.asi that has [agent] enabled=1?"
            ) from error
        if not line:
            self.close()
            raise BridgeUnavailable(
                "game state bridge closed the connection without an answer"
            )
        return json.loads(line)
