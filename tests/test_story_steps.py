import math
import unittest

from hypothesis import given, settings, strategies as st
from PIL import Image

from crimson_desert_agent.scripting.hud import Word, lines_from_words
from tests.doubles import RecordingCamera, engine_for
from tests.simulated_game import SimulatedGame

offsets = st.floats(min_value=-40, max_value=40, allow_nan=False)
headings = st.floats(min_value=0, max_value=360, allow_nan=False, exclude_max=True)
standoffs = st.floats(min_value=1.0, max_value=4.0, allow_nan=False)


def game_with_actor(
    offset_x: float, offset_z: float, camera_yaw: float
) -> SimulatedGame:
    game = SimulatedGame(position=(10.0, 50.0, 20.0), camera_yaw_degrees=camera_yaw)
    plain = game.read_state

    def with_actor() -> dict:
        state = plain()
        state["actors"] = [
            {
                "key": "0x51",
                "kind": "character",
                "position": [10.0 + offset_x, 50.0, 20.0 + offset_z],
            }
        ]
        return state

    game.read_state = with_actor
    return game


class ApproachTest(unittest.TestCase):
    @settings(deadline=None, max_examples=50)
    @given(offsets, offsets, headings, standoffs)
    def test_stops_at_the_standoff_facing_the_actor(
        self, offset_x, offset_z, camera_yaw, standoff
    ):
        if math.hypot(offset_x, offset_z) < 0.1:
            return
        game = game_with_actor(offset_x, offset_z, camera_yaw)
        answer = engine_for(game).run(f"approach 0x51 distance={standoff!r}")
        self.assertTrue(answer["ok"], answer)
        result = answer["steps"][0]["result"]
        self.assertTrue(result["facing"], result)
        remaining = math.hypot(
            10.0 + offset_x - game.position[0], 20.0 + offset_z - game.position[2]
        )
        self.assertLessEqual(
            remaining, max(standoff, math.hypot(offset_x, offset_z)) + 0.6
        )
        bearing = math.degrees(
            math.atan2(
                10.0 + offset_x - game.position[0], 20.0 + offset_z - game.position[2]
            )
        )
        self.assertLessEqual(
            abs((bearing - game.camera_yaw_degrees + 180) % 360 - 180), 5.5
        )
        self.assertTrue(game.is_idle())

    def test_names_the_missing_actor(self):
        answer = engine_for(game_with_actor(3.0, 3.0, 0.0)).run("approach 0x99")
        self.assertFalse(answer["ok"])
        self.assertIn("no actor '0x99'", answer["error"])


class HudTest(unittest.TestCase):
    def test_groups_confident_words_into_positioned_lines(self):
        words = [
            Word("with", 380, 801, 410, 93.0),
            Word("Speak", 320, 800, 370, 96.0),
            Word("Ross", 420, 802, 455, 91.0),
            Word("Talk", 560, 604, 590, 88.0),
            Word("~~", 700, 300, 720, 95.0),
            Word("blur", 900, 300, 930, 30.0),
            Word("frame", 20, 20, 60, 99.0),
        ]
        self.assertEqual(
            lines_from_words(words),
            [
                {"text": "Talk", "x": 560, "y": 604},
                {"text": "Speak with Ross", "x": 320, "y": 800},
            ],
        )

    def test_hud_step_reports_window_positions_for_a_cropped_read(self):
        camera = RecordingCamera()
        camera.capture = lambda: Image.new("RGB", (1600, 900))
        seen = []

        def read_words(frame):
            seen.append(frame.size)
            return [Word("Talk", 49, 4, 79, 90.0)]

        answer = engine_for(SimulatedGame(), camera=camera, read_words=read_words).run(
            "hud crop=500,600,300,60"
        )
        self.assertEqual(seen, [(300, 60)])
        self.assertEqual(
            answer["steps"][0]["result"], [{"text": "Talk", "x": 549, "y": 604}]
        )


if __name__ == "__main__":
    unittest.main()
