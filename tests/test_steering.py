import math
import unittest

from hypothesis import given, settings, strategies as st

from crimson_desert_agent.scripting.navigation import turn_degrees
from crimson_desert_agent.scripting.steering import Steering
from tests.simulated_game import SimulatedGame

headings = st.floats(min_value=0, max_value=360, allow_nan=False, exclude_max=True)
offsets = st.floats(min_value=-60, max_value=60, allow_nan=False)


def steering_for(game: SimulatedGame) -> Steering:
    return Steering(game.read_state, game, game.interrupted_within, game.clock)


class GoToTest(unittest.TestCase):
    @settings(deadline=None, max_examples=60)
    @given(offsets, offsets, headings)
    def test_reaches_any_ground_point_under_any_camera_heading_and_stops(
        self, offset_x, offset_z, camera_yaw
    ):
        game = SimulatedGame(
            position=(100.0, 50.0, -200.0), camera_yaw_degrees=camera_yaw
        )
        result = steering_for(game).go_to(
            100.0 + offset_x, -200.0 + offset_z, 1.0, 60.0
        )
        self.assertTrue(result.arrived, result)
        self.assertLessEqual(
            math.hypot(
                game.position[0] - 100.0 - offset_x, game.position[2] + 200.0 - offset_z
            ),
            1.0,
        )
        self.assertTrue(game.is_idle())

    def test_gives_up_when_stuck_and_releases_the_stick(self):
        game = SimulatedGame(blocked=True)
        result = steering_for(game).go_to(20.0, 0.0, 1.0, 30.0)
        self.assertFalse(result.arrived)
        self.assertTrue(result.reason.startswith("stuck"), result.reason)
        self.assertLess(result.elapsed_seconds, 4.0)
        self.assertTrue(game.is_idle())

    def test_reports_not_in_world_without_moving(self):
        game = SimulatedGame(in_world=False)
        result = steering_for(game).go_to(5.0, 5.0, 1.0, 5.0)
        self.assertFalse(result.arrived)
        self.assertTrue(
            result.reason.startswith("not in world: loading"), result.reason
        )
        self.assertEqual(
            [event for event in game.events if event[2] not in ((0.0, 0.0),)], []
        )

    def test_times_out(self):
        game = SimulatedGame(run_speed_m_per_second=1.0)
        result = steering_for(game).go_to(0.0, 500.0, 1.0, 2.0)
        self.assertEqual((result.arrived, result.reason), (False, "timeout"))
        self.assertTrue(game.is_idle())


class TurnToTest(unittest.TestCase):
    @settings(deadline=None, max_examples=80)
    @given(headings, headings, st.sampled_from([0.5, 1.0, 2.0]))
    def test_turns_the_camera_to_any_heading_by_the_short_way(
        self, start, target, turn_rate
    ):
        game = SimulatedGame(camera_yaw_degrees=start, turn_rate_scale=turn_rate)
        result = steering_for(game).turn_to(target, 3.0, 20.0)
        self.assertTrue(result.arrived, result)
        self.assertLessEqual(abs(turn_degrees(game.camera_yaw_degrees, target)), 3.0)
        self.assertTrue(game.is_idle())
        short_way_seconds = abs(turn_degrees(start, target)) / (60.0 * turn_rate) + 2.0
        self.assertLessEqual(result.elapsed_seconds, short_way_seconds)

    def test_reports_not_in_world(self):
        game = SimulatedGame(in_world=False)
        result = steering_for(game).turn_to(90.0, 3.0, 5.0)
        self.assertFalse(result.arrived)
        self.assertTrue(result.reason.startswith("not in world"), result.reason)


if __name__ == "__main__":
    unittest.main()
