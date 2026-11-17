import json
import socket

from .line_client import LineServiceUnavailable

MAXIMUM_DATAGRAM_BYTES = 65535


class DatagramSession:
    def __init__(
        self, service: str, host: str, port: int, timeout_seconds: float
    ) -> None:
        self._service = service
        self._address = (host, port)
        self._connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._connection.settimeout(timeout_seconds)
        self._connection.connect(self._address)

    def __enter__(self) -> "DatagramSession":
        return self

    def __exit__(self, *_: object) -> None:
        self._connection.close()

    def ask(self, command: str) -> dict:
        try:
            self._connection.send(command.encode())
            answer = self._connection.recv(MAXIMUM_DATAGRAM_BYTES)
        except OSError as error:
            raise LineServiceUnavailable(
                f"{self._service} did not answer on {self._address[0]}:{self._address[1]} ({error or 'timed out'})"
            ) from error
        try:
            return json.loads(answer)
        except ValueError as error:
            raise LineServiceUnavailable(
                f"{self._service} answered {answer[:80]!r}, not JSON"
            ) from error
