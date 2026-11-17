import math
import unittest

from hypothesis import given, strategies as st

from crimson_desert_agent.scripting.projection import box_around, screen_point
from crimson_desert_agent.scripting.staging import copy_error, stage_across_view

angles = st.floats(min_value=0, max_value=2 * math.pi, allow_nan=False)
metres = st.floats(min_value=-30, max_value=30, allow_nan=False)


def camera_at(yaw: float) -> dict:
    return {
        "position": [100.0, 52.0, -40.0],
        "forward": [math.sin(yaw), 0.0, math.cos(yaw)],
        "right": [math.cos(yaw), 0.0, -math.sin(yaw)],
    }


class StagingTest(unittest.TestCase):
    @given(angles, st.floats(min_value=0.5, max_value=30), metres, metres)
    def test_stage_points_sit_ahead_of_the_camera_at_the_asked_offsets(
        self, yaw, ahead, start, end
    ):
        camera = camera_at(yaw)
        staged = stage_across_view(
            {"camera": camera, "player": {"position": [0.0, 50.0, 0.0]}},
            ahead,
            start,
            end,
        )
        for (x, z), right_m in (
            ((staged.start[0], staged.start[2]), start),
            (staged.end, end),
        ):
            offset = [x - 100.0, 0.0, z + 40.0]
            self.assertAlmostEqual(
                sum(a * b for a, b in zip(offset, camera["forward"])), ahead, places=2
            )
            self.assertAlmostEqual(
                sum(a * b for a, b in zip(offset, camera["right"])), right_m, places=2
            )
        self.assertEqual(staged.start[1], 50.0)

    def test_copy_error_measures_the_copy_against_the_peer_body(self):
        peer = {"position": [10.0, 5.0, 20.0]}
        bridge = {
            "actors": [
                {"kind": "character", "position": [0, 0, 0]},
                {"kind": "coop_copy", "key": "0xA1", "position": [13.0, 5.5, 24.0]},
            ]
        }
        error = copy_error(peer, bridge)
        self.assertEqual(
            (error["ground_error_m"], error["height_error_m"], error["copy_key"]),
            (5.0, 0.5, "0xA1"),
        )
        self.assertEqual(copy_error(peer, {"actors": []}), {"copy_visible": False})


class ProjectionTest(unittest.TestCase):
    @given(
        angles,
        st.floats(min_value=1, max_value=80),
        st.floats(min_value=-0.4, max_value=0.4),
        st.floats(min_value=-0.2, max_value=0.2),
    )
    def test_a_point_lands_where_its_offsets_from_the_view_axis_put_it(
        self, yaw, depth, right_share, up_share
    ):
        camera = camera_at(yaw)
        half_height = math.tan(math.radians(25.0))
        half_width = half_height * 16 / 9
        point = [
            camera["position"][axis]
            + camera["forward"][axis] * depth
            + camera["right"][axis] * depth * half_width * right_share
            for axis in range(3)
        ]
        point[1] += depth * half_height * up_share
        x, y = screen_point(camera, point, 1600, 900, 50.0)
        self.assertAlmostEqual(x, 800 * (1 + right_share), delta=0.5)
        self.assertAlmostEqual(y, 450 * (1 - up_share), delta=0.5)

    def test_points_behind_the_camera_have_no_screen_point_and_boxes_stay_inside(self):
        self.assertIsNone(
            screen_point(camera_at(0.0), [100.0, 52.0, -50.0], 1600, 900, 50.0)
        )
        box = box_around((1590.0, 5.0), 400, 1600, 900)
        self.assertEqual(
            (box.left, box.top, box.width, box.height), (1200, 0, 400, 400)
        )


if __name__ == "__main__":
    unittest.main()
