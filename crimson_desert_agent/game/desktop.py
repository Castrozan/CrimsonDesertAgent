import json
import os
import socket
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


def hyprland(command: str) -> str:
    path = os.path.join(
        os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "hypr",
        os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", ""), ".socket.sock",
    )
    try:
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(5.0)
            connection.connect(path)
            connection.sendall(command.encode())
            chunks = []
            while chunk := connection.recv(65536):
                chunks.append(chunk)
    except OSError as error:
        raise DesktopError(f"Hyprland did not answer {command!r}: {error}") from error
    return b"".join(chunks).decode(errors="replace")


def game_window_geometry() -> str | None:
    for client in json.loads(hyprland("j/clients")):
        if client["title"] == GAME_WINDOW_TITLE:
            (left, top), (width, height) = client["at"], client["size"]
            return f"{left},{top} {width}x{height}"
    return None


def game_window_focused() -> bool:
    return json.loads(hyprland("j/activewindow")).get("title") == GAME_WINDOW_TITLE


def focus_game() -> None:
    answer = hyprland(f"dispatch focuswindow title:^{GAME_WINDOW_TITLE}$")
    if answer.strip() != "ok":
        raise DesktopError(f"could not focus the game window: {answer.strip()}")


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
