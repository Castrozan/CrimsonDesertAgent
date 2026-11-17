import os
import tempfile
import unittest
from unittest import mock

from crimson_desert_agent.game.session import adopt_graphical_session


class GraphicalSessionTest(unittest.TestCase):
    def test_fills_only_what_the_shell_lacks_from_the_running_session(self):
        with tempfile.TemporaryDirectory() as runtime:
            os.makedirs(os.path.join(runtime, "hypr", "older_1"))
            os.makedirs(os.path.join(runtime, "hypr", "newer_2"))
            os.utime(os.path.join(runtime, "hypr", "older_1"), (1, 1))
            open(os.path.join(runtime, "wayland-1"), "w").close()
            open(os.path.join(runtime, "wayland-1.lock"), "w").close()
            open(os.path.join(runtime, "xwayland-auth"), "w").close()
            with mock.patch.dict(
                os.environ,
                {"XDG_RUNTIME_DIR": runtime, "WAYLAND_DISPLAY": "wayland-7"},
                clear=True,
            ):
                adopt_graphical_session()
                self.assertEqual(os.environ["HYPRLAND_INSTANCE_SIGNATURE"], "newer_2")
                self.assertEqual(os.environ["WAYLAND_DISPLAY"], "wayland-7")
            with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": runtime}, clear=True):
                adopt_graphical_session()
                self.assertEqual(os.environ["WAYLAND_DISPLAY"], "wayland-1")
                self.assertEqual(
                    os.environ["XAUTHORITY"], os.path.join(runtime, "xwayland-auth")
                )


if __name__ == "__main__":
    unittest.main()
