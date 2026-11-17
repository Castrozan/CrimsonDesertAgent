import json
import subprocess

GAME_WINDOW_TITLE = "Crimson Desert"
SCREENSHOT_SCALE = "0.5"
SCREENSHOT_JPEG_QUALITY = "80"


class DesktopError(Exception):
    pass


def run(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DesktopError(f"{command[0]} failed: {error}") from error
    if completed.returncode != 0:
        raise DesktopError(
            f"{command[0]} failed: {completed.stderr.strip() or completed.stdout.strip()}"
        )
    return completed.stdout


def game_window_geometry() -> str | None:
    for client in json.loads(run(["hyprctl", "clients", "-j"])):
        if client["title"] == GAME_WINDOW_TITLE:
            (left, top), (width, height) = client["at"], client["size"]
            return f"{left},{top} {width}x{height}"
    return None


def focus_game() -> None:
    run(["hyprctl", "dispatch", "focuswindow", f"title:^{GAME_WINDOW_TITLE}$"])


def screenshot(path: str) -> None:
    geometry = game_window_geometry()
    region = ["-g", geometry] if geometry else []
    run(
        [
            "grim",
            *region,
            "-s",
            SCREENSHOT_SCALE,
            "-t",
            "jpeg",
            "-q",
            SCREENSHOT_JPEG_QUALITY,
            path,
        ]
    )
