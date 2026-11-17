import json
import socket


class LineServiceUnavailable(Exception):
    pass


class LineSession:
    def __init__(self, service: str, host: str, port: int, timeout_seconds: float) -> None:
        self._service = service
        self._address = (host, port)
        self._timeout_seconds = timeout_seconds
        self._connection: socket.socket | None = None
        self._stream = None

    def __enter__(self) -> "LineSession":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        self._stream = None

    def ask(self, line: str) -> dict:
        try:
            if self._connection is None:
                self._connection = socket.create_connection(self._address, timeout=self._timeout_seconds)
                self._connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self._stream = self._connection.makefile("r", encoding="utf-8")
            self._connection.sendall(line.encode() + b"\n")
            answer = self._stream.readline()
        except OSError as error:
            self.close()
            raise LineServiceUnavailable(
                f"{self._service} not reachable on {self._address[0]}:{self._address[1]} ({error})"
            ) from error
        if not answer:
            self.close()
            raise LineServiceUnavailable(f"{self._service} closed the connection without an answer")
        try:
            return json.loads(answer)
        except ValueError as error:
            raise LineServiceUnavailable(f"{self._service} answered {answer.strip()!r}, not JSON") from error
