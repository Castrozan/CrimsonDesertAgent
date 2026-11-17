from .line_client import LineServiceUnavailable, LineSession

BridgeUnavailable = LineServiceUnavailable


class BridgeSession(LineSession):
    def __init__(self, host: str, port: int, timeout_seconds: float) -> None:
        super().__init__(
            "the game state bridge (a running game with cdmp.asi and [agent] enabled=1)",
            host, port, timeout_seconds,
        )

    def read_state(self) -> dict:
        return self.ask("state")
