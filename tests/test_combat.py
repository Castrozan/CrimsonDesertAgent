import math
import unittest

from tests.doubles import engine_for
from tests.simulated_game import SimulatedGame


def game_with_enemy(distance: float, hits: bool = False) -> SimulatedGame:
    game = SimulatedGame(position=(0.0, 50.0, 0.0))
    plain = game.read_state
    health = [300.0]

    def with_enemy() -> dict:
        state = plain()
        enemy = [game.position[0], 50.0, game.position[2] + distance]
        if hits and "lb" not in game.pressed:
            health[0] -= 1.0
        state["player"]["health"] = health[0]
        state["actors"] = [
            {
                "key": "0xE1",
                "kind": "character",
                "position": enemy,
                "distance": distance,
            }
        ]
        return state

    game.read_state = with_enemy
    return game


class HoldGroundTest(unittest.TestCase):
    def test_guards_near_an_enemy_strikes_in_reach_and_ends_idle(self):
        game = game_with_enemy(2.0)
        result = engine_for(game).run("fight 0 0 seconds=12")["steps"][0]["result"]
        self.assertEqual(result["ended"], "time")
        self.assertGreaterEqual(result["strikes"], 3)
        held = sum(
            1 for _, name, pressed in game.events if name == "lb" and pressed is True
        )
        self.assertGreaterEqual(held, 1)
        self.assertTrue(game.is_idle())
        self.assertLessEqual(math.hypot(game.position[0], game.position[2]), 5.0)

    def test_does_not_strike_an_enemy_out_of_reach(self):
        result = engine_for(game_with_enemy(4.0)).run("fight 0 0 seconds=6")["steps"][
            0
        ]["result"]
        self.assertEqual(result["strikes"], 0)

    def test_withholds_a_strike_that_would_lunge_into_fire(self):
        answer = engine_for(game_with_enemy(2.0)).run("hazard 0 3; fight 0 0 seconds=6")
        result = answer["steps"][1]["result"]
        self.assertEqual(result["strikes"], 0)
        self.assertGreaterEqual(result["strikes_withheld_near_fire"], 1)

    def test_returns_to_the_anchor_when_outside_the_leash(self):
        game = game_with_enemy(9.0)
        game.position[0] = 12.0
        result = engine_for(game).run("fight 0 0 seconds=6 leash=3")["steps"][0][
            "result"
        ]
        self.assertGreaterEqual(result["returns_to_anchor"], 1)
        self.assertLessEqual(math.hypot(game.position[0], game.position[2]), 3.0)

    def test_stops_when_the_player_dies(self):
        game = game_with_enemy(9.0)
        plain = game.read_state
        game.read_state = lambda: {
            **plain(),
            "player": {**plain()["player"], "health": 0.0},
        }
        self.assertEqual(
            engine_for(game).run("fight 0 0")["steps"][0]["result"]["ended"], "died"
        )


if __name__ == "__main__":
    unittest.main()
