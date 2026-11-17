import math
import unittest

from hypothesis import given, settings, strategies as st

from tests.doubles import ScriptedScreen, engine_for, quest_block, words
from tests.simulated_game import SimulatedGame

offsets = st.floats(min_value=-40, max_value=40, allow_nan=False)
headings = st.floats(min_value=0, max_value=360, allow_nan=False, exclude_max=True)
standoffs = st.floats(min_value=1.0, max_value=4.0, allow_nan=False)


def game_with_actor(
    offset_x: float, offset_z: float, camera_yaw: float = 0.0, **options
) -> SimulatedGame:
    game = SimulatedGame(
        position=(10.0, 50.0, 20.0), camera_yaw_degrees=camera_yaw, **options
    )
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


def played(game: SimulatedGame, script: str, screen=None, read_marker=None) -> dict:
    if screen is not None:
        screen.game = game
    answer = engine_for(game, read_words=screen, read_marker=read_marker).run(script)
    assert answer["ok"], answer
    return answer["steps"][-1]["result"]


class ApproachTest(unittest.TestCase):
    @settings(deadline=None, max_examples=40)
    @given(offsets, offsets, headings, standoffs)
    def test_stops_at_the_standoff_facing_the_actor(
        self, offset_x, offset_z, camera_yaw, standoff
    ):
        if math.hypot(offset_x, offset_z) < 0.1:
            return
        game = game_with_actor(offset_x, offset_z, camera_yaw)
        result = played(game, f"approach 0x51 distance={standoff!r}")
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

    def test_a_vanished_actor_is_skipped_and_the_script_goes_on(self):
        answer = engine_for(game_with_actor(3.0, 3.0)).run("approach 0x99; state")
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(
            answer["steps"][0]["result"], {"skipped": "actor gone", "actor": "0x99"}
        )
        self.assertEqual(len(answer["steps"]), 2)

    def test_reports_not_facing_when_the_walk_is_blocked(self):
        result = played(game_with_actor(0.0, 20.0, blocked=True), "approach 0x51")
        self.assertEqual((result["facing"], result["talk_prompt"]), (False, False))
        self.assertTrue(result["walk"].startswith("stuck"), result)

    def test_learns_the_name_and_accepts_it_afterwards(self):
        screen = ScriptedScreen(
            lambda seconds: (
                quest_block("Gather information")
                + words("Talk", 760, 500)
                + words("Ross", 800, 300)
            )
        )
        game = game_with_actor(0.0, 6.0)
        first = played(game, "approach 0x51", screen)
        self.assertEqual((first["name"], first["talk_prompt"]), ("Ross", True))
        engine = engine_for(game, read_words=screen)
        answer = engine.run("approach 0x51; approach ross; status")
        self.assertEqual(answer["steps"][1]["result"]["key"], "0x51")
        self.assertEqual(answer["steps"][2]["result"]["actors"][0]["name"], "Ross")


class GoAroundTest(unittest.TestCase):
    def test_goto_sidesteps_an_obstacle_and_arrives(self):
        game = SimulatedGame(position=(0.0, 50.0, 0.0), obstacle=(0.0, 8.0, 2.0))
        result = played(game, "goto 0 20")
        self.assertTrue(result["arrived"], result)
        self.assertGreaterEqual(result["detours"], 1)

    def test_goto_reports_stuck_after_three_detours(self):
        result = played(SimulatedGame(blocked=True), "goto 0 20")
        self.assertEqual((result["arrived"], result["detours"]), (False, 3))


class TalkTest(unittest.TestCase):
    def conversation(self, seconds: float):
        if seconds < 3.0:
            return quest_block("Check on your comrades") + words(
                "Speak with Ross.", 500, 830
            )
        if seconds < 9.0:
            return words("Ross", 760, 660) + words("We lost the trail.", 600, 700)
        return quest_block("Gather information") + words(
            "Ask around the camp.", 500, 830
        )

    def test_talks_without_pressing_and_reports_what_changed(self):
        game = game_with_actor(0.0, 4.0)
        result = played(game, "talk 0x51", ScriptedScreen(self.conversation))
        self.assertTrue(result["started"], result)
        self.assertIsNone(result["halted"])
        self.assertEqual(result["spoken"], ["Ross", "We lost the trail."])
        self.assertEqual(
            result["quest_after"], ["Unfamiliar Lands", "Gather information"]
        )
        self.assertEqual(
            (result["guide_before"], result["guide_after"]),
            ("Speak with Ross.", "Ask around the camp."),
        )
        self.assertEqual(
            {name for _, name, pressed in game.events if pressed is True}, {"x"}
        )

    def test_halts_on_an_exit_prompt_without_confirming(self):
        game = game_with_actor(0.0, 4.0)
        screen = ScriptedScreen(lambda seconds: words("Exit to Title ?", 700, 400))
        result = played(game, "talk 0x51", screen)
        self.assertEqual(result["halted"], "exit")
        self.assertNotIn(
            "a", {name for _, name, pressed in game.events if pressed is True}
        )


class MarkerTest(unittest.TestCase):
    def test_walks_legs_toward_the_minimap_marker_until_close(self):
        game = SimulatedGame(position=(0.0, 50.0, 0.0), camera_yaw_degrees=70.0)
        target = (30.0, 40.0)

        def minimap(frame):
            right, ahead = target[0] - game.position[0], target[1] - game.position[2]
            yaw = math.radians(game.camera_yaw_degrees)
            reach = 60 / max(math.hypot(right, ahead), 1.0)
            return {
                "right": (right * math.cos(yaw) - ahead * math.sin(yaw)) * reach,
                "down": -(right * math.sin(yaw) + ahead * math.cos(yaw)) * reach,
                "metres": round(math.hypot(right, ahead)),
            }

        shown = ScriptedScreen(lambda seconds: quest_block("Gather information"))
        result = played(game, "marker", shown, minimap)
        self.assertTrue(result["arrived"], result)
        self.assertLessEqual(
            math.hypot(target[0] - game.position[0], target[1] - game.position[2]), 6.0
        )

    def test_reports_a_missing_marker_and_a_hidden_hud(self):
        shown = ScriptedScreen(lambda seconds: quest_block("Gather information"))
        self.assertEqual(
            played(SimulatedGame(), "marker", shown)["reason"],
            "no marker distance on the minimap",
        )
        self.assertIn("press nothing", played(SimulatedGame(), "marker")["reason"])


if __name__ == "__main__":
    unittest.main()
