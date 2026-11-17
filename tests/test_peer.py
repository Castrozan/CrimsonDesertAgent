import json
import socketserver
import threading
import unittest

from crimson_desert_agent.game.line_client import LineSession
from crimson_desert_agent.peer import run_peer_script


class RecordingPeer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self) -> None:
        self.received: list[str] = []
        self.connections = 0
        super().__init__(("127.0.0.1", 0), PeerHandler)


class PeerHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.server.connections += 1
        for raw in self.rfile:
            line = raw.decode().strip()
            self.server.received.append(line)
            if line == "hang up":
                return
            answer = "not json" if line == "garble" else json.dumps({"ok": True, "echo": line})
            self.wfile.write(answer.encode() + b"\n")


class PeerScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.peer = RecordingPeer()
        threading.Thread(target=self.peer.serve_forever, daemon=True).start()
        self.addCleanup(self.peer.server_close)
        self.addCleanup(self.peer.shutdown)
        self.slept: list[float] = []

    def run_script(self, script: str) -> dict:
        port = self.peer.server_address[1]
        return run_peer_script(script, lambda: LineSession("the peer control port", "127.0.0.1", port, 2.0),
                               sleep=self.slept.append)

    def test_commands_reach_the_peer_in_order_over_one_connection(self):
        answer = self.run_script("goto 10 -4; wait 1.5; face 90\nstate")
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(self.peer.received, ["goto 10 -4", "face 90", "state"])
        self.assertEqual(self.peer.connections, 1)
        self.assertEqual(self.slept, [1.5])
        self.assertEqual([step.get("result", {}).get("echo") for step in answer["steps"]],
                         ["goto 10 -4", None, "face 90", "state"])

    def test_a_wait_the_plugin_cannot_read_goes_to_the_peer(self):
        self.run_script("wait for arrival; wait 500")
        self.assertEqual(self.peer.received, ["wait for arrival", "wait 500"])
        self.assertEqual(self.slept, [])

    def test_a_dropped_or_garbled_answer_stops_the_script_and_names_the_command(self):
        for failing in ("hang up", "garble"):
            answer = self.run_script(f"state; {failing}; face 90")
            self.assertFalse(answer["ok"])
            self.assertTrue(answer["error"].startswith(f"{failing}: the peer control port"), answer["error"])
            self.assertNotIn("face 90", self.peer.received)

    def test_an_absent_peer_is_reported(self):
        answer = run_peer_script("state", lambda: LineSession("the peer control port", "127.0.0.1", 1, 0.5))
        self.assertEqual(answer["ok"], False)
        self.assertIn("not reachable on 127.0.0.1:1", answer["error"])

    def test_an_empty_script_is_rejected(self):
        self.assertFalse(run_peer_script(" ; ")["ok"])


if __name__ == "__main__":
    unittest.main()
