import unittest

from crimson_desert_agent.scripting.script import ScriptError, parse
from crimson_desert_agent.story.hud_layout import describe
from crimson_desert_agent.story.screen_lines import Word, lines_from_words
from tests.doubles import ScriptedScreen, engine_for, quest_block, words
from tests.simulated_game import SimulatedGame


class HudTest(unittest.TestCase):
    def test_groups_confident_words_into_positioned_lines(self):
        seen = [
            Word("with", 380, 801, 410, 93.0),
            Word("Speak", 320, 800, 370, 96.0),
            Word("Ross", 420, 802, 455, 91.0),
            Word("Talk", 560, 604, 590, 88.0),
            Word("(1/3)", 600, 605, 640, 88.0),
            Word("~~", 700, 300, 720, 95.0),
            Word("blur", 900, 300, 930, 30.0),
            Word("frame", 20, 20, 60, 99.0),
        ]
        self.assertEqual(
            lines_from_words(seen),
            [
                {"text": "Talk (1/3)", "x": 560, "y": 604},
                {"text": "Speak with Ross", "x": 320, "y": 800},
            ],
        )

    def test_sorts_the_live_frame_into_quest_guide_and_marker(self):
        lines = [
            {"text": "cdmp_peer", "x": 1242, "y": 554},
            {"text": "3m", "x": 1260, "y": 590},
            {"text": "Unfamiliar Lands", "x": 74, "y": 652},
            {"text": "Gather information", "x": 92, "y": 691},
            {"text": "Day 14 Sun 11:10 PM", "x": 63, "y": 749},
            {"text": "Hills of No Return", "x": 66, "y": 800},
            {"text": "Speak with your comrades.", "x": 667, "y": 960},
            {"text": "Ask around the cabin.", "x": 667, "y": 1000},
        ]
        state = {
            "camera_heading_degrees": 353.4,
            "position": [-9828.85, 614.6, -2823.37],
        }
        report = describe(
            lines, (1920, 1080), state, {"right": -24.0, "down": -60.0, "metres": 20}
        )
        self.assertEqual(
            (report["quest"], report["objectives"]),
            ("Unfamiliar Lands", ["Gather information"]),
        )
        self.assertEqual(
            (report["guide"], report["marker_m"], report["other"]),
            ("Ask around the cabin.", 20, []),
        )
        self.assertAlmostEqual(report["marker_bearing_degrees"], 330.0, delta=8.0)
        self.assertEqual(report["place"], ["Day 14 Sun 11:10 PM", "Hills of No Return"])
        self.assertFalse(report["exit_prompt"])

    def test_hud_step_reads_a_crop_in_window_positions(self):
        sizes = []

        def read_words(frame):
            sizes.append(frame.size)
            return [Word("Talk", 49, 4, 79, 90.0)]

        answer = engine_for(SimulatedGame(), read_words=read_words).run(
            "hud crop=500,600,300,60"
        )
        self.assertEqual(sizes, [(300, 60)])
        self.assertEqual(answer["steps"][0]["result"]["prompt"]["x"], 549)


class ConfirmGuardTest(unittest.TestCase):
    def paused_game(self) -> SimulatedGame:
        game = SimulatedGame()
        plain = game.read_state
        game.read_state = lambda: {**plain(), "paused": True}
        return game

    def run_with(self, game, script, screen_words):
        screen = ScriptedScreen(lambda seconds: screen_words)
        screen.game = game
        return engine_for(game, read_words=screen).run(script)

    def test_refuses_to_confirm_blind_while_paused(self):
        game = self.paused_game()
        answer = self.run_with(game, "press a", quest_block("Gather information"))
        self.assertFalse(answer["ok"])
        self.assertIn("read hud", answer["error"])
        self.assertEqual([event for event in game.events if event[1] == "a"], [])

    def test_allows_one_confirm_after_each_hud_read(self):
        answer = self.run_with(
            self.paused_game(), "hud; press a; press a", words("Next", 700, 400)
        )
        self.assertFalse(answer["ok"])
        self.assertEqual(len(answer["steps"]), 3)

    def test_never_confirms_an_exit_prompt(self):
        game = SimulatedGame()
        answer = self.run_with(
            game, "hud; press start", words("Quit the game ?", 700, 400)
        )
        self.assertIn("exit prompt", answer["error"])
        self.assertTrue(
            self.run_with(game, "hud; press b", words("Quit the game ?", 700, 400))[
                "ok"
            ]
        )


class ParserHintTest(unittest.TestCase):
    def test_suggests_the_reordered_step(self):
        with self.assertRaises(ScriptError) as raised:
            parse("hold x 1")
        self.assertIn("Did you mean 'hold 1 x'?", str(raised.exception))


class AttackProofTest(unittest.TestCase):
    def test_reports_only_hashes_new_since_the_idle_window(self):
        game = SimulatedGame()
        idle = [
            {
                "seconds": 10.0 + tick,
                "first_hash": "71C87643",
                "second_hash": "00000000",
            }
            for tick in range(5)
        ]
        swing = {"seconds": 16.0, "first_hash": "ECF9B7D2", "second_hash": "FBD56B20"}

        def recording(last):
            pressed = any(name == "rb" for _, name, _ in game.events)
            return {
                "ok": True,
                "start_actions": idle
                + ([swing, {**idle[0], "seconds": 16.5}] if pressed else []),
            }

        answer = engine_for(game, read_start_actions=recording).run("prove_attack")
        result = answer["steps"][0]["result"]
        self.assertEqual((result["proven"], result["new_actions"]), (True, [swing]))
        quiet = engine_for(
            SimulatedGame(),
            read_start_actions=lambda last: {"ok": True, "start_actions": idle},
        )
        self.assertFalse(
            quiet.run("prove_attack wait=2")["steps"][0]["result"]["proven"]
        )


class FireHazardTest(unittest.TestCase):
    def burning_game(self, fire=(0.0, 10.0), radius=2.0) -> SimulatedGame:
        game = SimulatedGame(position=(0.0, 50.0, 0.0))
        plain = game.read_state
        health = [300.0]

        def with_fire() -> dict:
            state = plain()
            if (
                (game.position[0] - fire[0]) ** 2 + (game.position[2] - fire[1]) ** 2
            ) ** 0.5 < radius:
                health[0] -= 4.0
            state["player"]["health"] = health[0]
            return state

        game.read_state = with_fire
        return game

    def test_a_walk_into_fire_stops_retreats_and_later_walks_go_round(self):
        game = self.burning_game()
        engine = engine_for(game)
        first = engine.run("goto 0 20; status")
        walked = first["steps"][0]["result"]
        self.assertTrue(walked["reason"].startswith("burning"), walked)
        self.assertIn("retreated_to", walked)
        self.assertEqual(len(first["steps"][1]["result"]["fire_hazards"]), 1)
        health_after_retreat = game.read_state()["player"]["health"]
        second = engine.run("goto 0 20")["steps"][0]["result"]
        self.assertTrue(second["arrived"], second)
        self.assertEqual(game.read_state()["player"]["health"], health_after_retreat)
        self.assertIn(
            "refused", engine.run("goto 0 8.5")["steps"][0]["result"]["reason"]
        )


if __name__ == "__main__":
    unittest.main()
