import glob
import os


def newest(pattern: str) -> str | None:
    matches = sorted(glob.glob(pattern), key=os.path.getmtime)
    return os.path.basename(matches[-1]) if matches else None


def adopt_graphical_session() -> None:
    runtime = os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    found = {
        "HYPRLAND_INSTANCE_SIGNATURE": newest(os.path.join(runtime, "hypr", "*")),
        "WAYLAND_DISPLAY": newest(os.path.join(runtime, "wayland-[0-9]")),
    }
    display = newest("/tmp/.X11-unix/X[0-9]*")
    found["DISPLAY"] = f":{display[1:]}" if display else None
    authority = os.path.join(runtime, "xwayland-auth")
    found["XAUTHORITY"] = authority if os.path.exists(authority) else None
    for name, value in found.items():
        if value and not os.environ.get(name):
            os.environ[name] = value
