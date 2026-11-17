import json
import socketserver
import threading
import unittest

from crimson_desert_agent.game.datagram_client import DatagramSession
from crimson_desert_agent.peer import run_peer_script


class RecordingPeer(socketserver.ThreadingUDPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self) -> None:
        self.received: list[str] = []
        super().__init__(("127.0.0.1", 0), PeerHandler)


class PeerHandler(socketserver.DatagramRequestHandler):
    def handle(self) -> None:
        command = self.rfile.read().decode()
        self.server.received.append(command)
        if command != "be silent":
            self.wfile.write(b"not json" if command == "garble" else json.dumps({"ok": True, "echo": command}).encode())

    def finish(self) -> None:
        if self.wfile.getvalue():
            super().finish()


class PeerScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.peer = RecordingPeer()
        threading.Thread(target=self.peer.serve_forever, daemon=True).start()
        self.addCleanup(self.peer.server_close)
        self.addCleanup(self.peer.shutdown)
        self.slept: list[float] = []

    def run_script(self, script: str, port: int | None = None) -> dict:
        port = port or self.peer.server_address[1]
        return run_peer_script(script, lambda: DatagramSession("the peer control port", "127.0.0.1", port, 0.3),
                               sleep=self.slept.append)

    def test_each_command_is_one_datagram_in_order(self):
        answer = self.run_script("goto 10 -4; wait 1.5; face 90\nstate")
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(self.peer.received, ["goto 10 -4", "face 90", "state"])
        self.assertEqual(self.slept, [1.5])
        self.assertEqual([step.get("result", {}).get("echo") for step in answer["steps"]],
                         ["goto 10 -4", None, "face 90", "state"])

    def test_a_wait_the_plugin_cannot_read_goes_to_the_peer(self):
        self.run_script("wait for arrival; wait 500")
        self.assertEqual(self.peer.received, ["wait for arrival", "wait 500"])
        self.assertEqual(self.slept, [])

    def test_a_missing_or_garbled_answer_stops_the_script_and_names_the_command(self):
        for failing in ("be silent", "garble"):
            answer = self.run_script(f"state; {failing}; face 90")
            self.assertFalse(answer["ok"])
            self.assertTrue(answer["error"].startswith(f"{failing}: the peer control port"), answer["error"])
            self.assertNotIn("face 90", self.peer.received)

    def test_an_absent_peer_is_reported(self):
        answer = self.run_script("state", port=1)
        self.assertEqual(answer["ok"], False)
        self.assertIn("did not answer on 127.0.0.1:1", answer["error"])

    def test_an_empty_script_is_rejected(self):
        self.assertFalse(run_peer_script(" ; ")["ok"])


if __name__ == "__main__":
    unittest.main()
