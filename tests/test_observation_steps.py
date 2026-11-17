import unittest

from tests.doubles import RecordingCamera, RecordingDesktop, RecordingPeer, engine_for
from tests.simulated_game import SimulatedGame


class ObservationStepsTest(unittest.TestCase):
    def test_state_carries_fields_a_newer_mod_adds(self):
        game = SimulatedGame()
        plain = game.read_state

        def newer() -> dict:
            state = plain()
            state["menu_open"] = True
            state["actors"] = [
                {"key": key, "distance": key + 0.26, "position": [1.26, 2.0, 3.0]}
                for key in range(9)
            ]
            state["player"]["stance"] = "crouched"
            return state

        game.read_state = newer
        state, status = (
            step["result"] for step in engine_for(game).run("state; status")["steps"]
        )
        self.assertEqual(
            (state["menu_open"], state["stance"], state["actors_in_range"]),
            (True, "crouched", 9),
        )
        self.assertEqual(
            state["actors"][0], {"key": 0, "distance": 0.3, "position": [1.3, 2.0, 3.0]}
        )
        self.assertEqual((len(state["actors"]), len(status["actors"])), (4, 9))

    def test_observation_steps_return_results(self):
        game = SimulatedGame(position=(1.0, 2.0, 3.0), camera_yaw_degrees=90.0)
        desktop = RecordingDesktop()
        answer = engine_for(game, desktop).run(
            "focus; state; shot /tmp/x.jpg; log; turn 180; goto 1 30 rb"
        )
        results = [step.get("result") for step in answer["steps"]]
        self.assertEqual(results[1]["position"], [1.0, 2.0, 3.0])
        self.assertEqual(results[1]["camera_heading_degrees"], 90.0)
        self.assertEqual(
            (results[2], results[3]),
            ({"path": "/tmp/x.jpg", "frames": 1}, ["World: loaded"]),
        )
        self.assertTrue(results[4]["arrived"] and results[5]["arrived"], results)
        self.assertEqual(desktop.calls, [("focus",)])
        self.assertIn(
            (0.0, "rb", True),
            [(0.0, name, value) for _, name, value in game.events if name == "rb"],
        )

    def test_a_burst_takes_its_frames_at_the_interval_and_crops_each(self):
        game, camera = SimulatedGame(), RecordingCamera()
        answer = engine_for(game, camera=camera).run(
            "shot /tmp/b.jpg burst=3 every=0.5 crop=10,20,300,200 scale=1 brightness=2"
        )
        self.assertAlmostEqual(answer["elapsed_ms"], 1000.0, delta=0.2)
        self.assertEqual(
            camera.written, [("/tmp/b.jpg", 3, [(10, 20, 300, 200)] * 3, 1.0, 2.0)]
        )

    def test_a_shot_around_an_actor_crops_where_the_camera_sees_it(self):
        game, camera = (
            SimulatedGame(position=(0.0, 0.0, 0.0), camera_yaw_degrees=0.0),
            RecordingCamera(),
        )
        plain = game.read_state

        def with_actor() -> dict:
            state = plain()
            state["actors"] = [
                {"key": "0xA1", "kind": "coop_copy", "position": [0.0, -1.0, 10.0]}
            ]
            return state

        game.read_state = with_actor
        answer = engine_for(game, camera=camera).run(
            "shot /tmp/a.jpg actor=coop_copy size=400"
        )
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(camera.written[0][2], [(600, 250, 400, 400)])
        missing = engine_for(game, camera=camera).run("shot /tmp/a.jpg actor=0xFF")
        self.assertIn("no actor '0xFF'", missing["error"])

    def test_teach_walks_the_player_until_the_peer_has_learnt_then_stops(self):
        game, peer = SimulatedGame(), RecordingPeer(lessons_after=2)
        answer = engine_for(game, peer=peer).run("teach timeout=10")
        result = answer["steps"][0]["result"]
        self.assertEqual((result["taught"], peer.asked), (True, 3))
        self.assertAlmostEqual(result["elapsed_seconds"], 2.6, places=2)
        self.assertTrue(game.is_idle())
        slow = engine_for(SimulatedGame(), peer=RecordingPeer(lessons_after=99)).run(
            "teach timeout=3"
        )
        self.assertFalse(slow["steps"][0]["result"]["taught"])


if __name__ == "__main__":
    unittest.main()
