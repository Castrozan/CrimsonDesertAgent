import unittest

from hypothesis import given, strategies as st

from crimson_desert_agent.game.bridge_client import BridgeUnavailable
from crimson_desert_agent.game.desktop import DesktopError
from crimson_desert_agent.scripting.engine import Engine
from tests.simulated_game import SimulatedGame


class RecordingDesktop:
    def __init__(self, fails: bool = False) -> None:
        self.calls: list[tuple] = []
        self.fails = fails

    def focus_game(self) -> None:
        if self.fails:
            raise DesktopError("no game window")
        self.calls.append(("focus",))

    def game_window_focused(self) -> bool:
        return not self.fails

    def screenshot(self, path: str) -> None:
        self.calls.append(("shot", path))


class FixedLog:
    def new_lines(self) -> list[str]:
        return ["World: loaded"]


def engine_for(game: SimulatedGame, desktop: RecordingDesktop | None = None) -> Engine:
    return Engine(
        game,
        lambda: game,
        desktop or RecordingDesktop(),
        FixedLog(),
        game.interrupted_within,
        game.clock,
    )


timed_steps = st.one_of(
    st.floats(min_value=0, max_value=3).map(
        lambda seconds: (f"wait {seconds:.3f}", round(seconds, 3))
    ),
    st.floats(min_value=0, max_value=3).map(
        lambda seconds: (f"hold {seconds:.3f} a rb", round(seconds, 3))
    ),
    st.floats(min_value=0, max_value=3).map(
        lambda seconds: (f"move 0.5 1 {seconds:.3f} lb", round(seconds, 3))
    ),
    st.floats(min_value=0, max_value=3).map(
        lambda seconds: (f"look -1 0.2 {seconds:.3f}", round(seconds, 3))
    ),
    st.floats(min_value=0, max_value=1).map(
        lambda seconds: (f"press x {seconds:.3f} 0", round(seconds, 3))
    ),
    st.sampled_from(
        [
            ("down lt", 0.0),
            ("up lt", 0.0),
            ("stick left 0 1", 0.0),
            ("release", 0.0),
            ("state", 0.0),
        ]
    ),
)


class EngineTest(unittest.TestCase):
    @given(st.lists(timed_steps, min_size=1, max_size=10))
    def test_a_script_takes_exactly_its_requested_time_and_leaves_the_pad_idle(
        self, steps
    ):
        game = SimulatedGame()
        answer = engine_for(game).run("; ".join(text for text, _ in steps))
        self.assertTrue(answer["ok"], answer)
        self.assertAlmostEqual(
            answer["elapsed_ms"], sum(seconds for _, seconds in steps) * 1000, delta=0.2
        )
        self.assertEqual(len(answer["steps"]), len(steps))
        self.assertTrue(game.is_idle())
        self.assertEqual(game.closed_bridges, 1)

    def test_overlapping_inputs_happen_at_their_scripted_instants(self):
        game = SimulatedGame()
        engine_for(game).run(
            "down lt; wait 0.3; press x 0.05 0.05; stick left 0 1; wait 0.2; up lt"
        )
        self.assertEqual(
            game.events[:6],
            [
                (0.0, "lt", True),
                (0.3, "x", True),
                (0.35, "x", False),
                (0.4, "left_stick", (0.0, 1.0)),
                (0.6, "lt", False),
                (0.6, "release_all", None),
            ],
        )

    def test_an_invalid_script_sends_no_input(self):
        game = SimulatedGame()
        answer = engine_for(game).run("press a; hold 1; press b")
        self.assertFalse(answer["ok"])
        self.assertIn("hold 1", answer["error"])
        self.assertEqual(game.events, [])

    def test_abort_stops_mid_step_and_releases_everything(self):
        game = SimulatedGame()
        game.abort_at = game.now + 0.5
        answer = engine_for(game).run("move 0 1 5 rb; press a")
        self.assertEqual(
            (answer["ok"], answer["error"]), (False, "move 0 1 5 rb: aborted")
        )
        self.assertAlmostEqual(answer["elapsed_ms"], 500.0, delta=0.2)
        self.assertTrue(game.is_idle())
        self.assertEqual(len(answer["steps"]), 1)

    def test_a_lost_bridge_stops_the_script_and_releases_everything(self):
        game = SimulatedGame()

        def unreachable() -> dict:
            raise BridgeUnavailable("bridge down")

        game.read_state = unreachable
        answer = engine_for(game).run("down rb; state; press a")
        self.assertEqual((answer["ok"], answer["error"]), (False, "state: bridge down"))
        self.assertTrue(game.is_idle())

    def test_a_desktop_failure_is_reported(self):
        game = SimulatedGame()
        answer = engine_for(game, RecordingDesktop(fails=True)).run("focus; press a")
        self.assertEqual(answer["error"], "focus: no game window")
        self.assertNotIn(("a", True), [(name, value) for _, name, value in game.events])

    def test_status_reports_speed_focus_and_what_the_pad_holds(self):
        game = SimulatedGame(run_speed_m_per_second=4.0)
        answer = engine_for(game).run("down lt; stick left 0 1; status")
        status = answer["steps"][2]["result"]
        self.assertAlmostEqual(status["ground_speed_m_per_second"], 4.0, places=2)
        self.assertTrue(status["game_window_focused"])
        self.assertEqual(status["pad"], {"held": ["lt"], "left_stick": [0.0, 1.0], "right_stick": [0.0, 0.0]})

    def test_observation_steps_return_results(self):
        game = SimulatedGame(position=(1.0, 2.0, 3.0), camera_yaw_degrees=90.0)
        desktop = RecordingDesktop()
        answer = engine_for(game, desktop).run(
            "focus; state; shot /tmp/x.jpg; log; turn 180; goto 1 30 rb"
        )
        results = [step.get("result") for step in answer["steps"]]
        self.assertEqual(results[1]["position"], [1.0, 2.0, 3.0])
        self.assertEqual(results[1]["camera_heading_degrees"], 90.0)
        self.assertEqual((results[2], results[3]), ("/tmp/x.jpg", ["World: loaded"]))
        self.assertTrue(results[4]["arrived"] and results[5]["arrived"], results)
        self.assertEqual(desktop.calls, [("focus",), ("shot", "/tmp/x.jpg")])
        self.assertIn(
            (0.0, "rb", True),
            [(0.0, name, value) for _, name, value in game.events if name == "rb"],
        )


if __name__ == "__main__":
    unittest.main()
