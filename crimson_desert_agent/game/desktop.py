import json
import os
import socket
import subprocess

GAME_WINDOW_TITLE = "Crimson Desert"


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
        os.environ.get("XDG_RUNTIME_DIR", "/tmp"),
        "hypr",
        os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", ""),
        ".socket.sock",
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
    window = f"title:^{GAME_WINDOW_TITLE}$"
    for command in (
        f"dispatch focuswindow {window}",
        f"dispatch alterzorder top,{window}",
    ):
        answer = hyprland(command).strip()
        if answer != "ok":
            raise DesktopError(f"Hyprland refused {command!r}: {answer}")


def run_bytes(command: list[str]) -> bytes:
    try:
        completed = subprocess.run(command, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DesktopError(f"{command[0]} failed: {error}") from error
    if completed.returncode != 0:
        raise DesktopError(
            f"{command[0]} failed: {completed.stderr.decode(errors='replace').strip()}"
        )
    return completed.stdout
