import time

from evdev import UInput, ecodes

from .desktop import hyprland

DEVICE_SETTLE_SECONDS = 1.0
CLICK_SECONDS = 0.12


def click(x: int, y: int) -> None:
    device = UInput(
        {ecodes.EV_KEY: [ecodes.BTN_LEFT], ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y]},
        name="crimson-desert-agent pointer",
    )
    try:
        time.sleep(DEVICE_SETTLE_SECONDS)
        hyprland(f"dispatch movecursor {x} {y}")
        time.sleep(0.2)
        device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1)
        device.syn()
        time.sleep(CLICK_SECONDS)
        device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
        device.syn()
    finally:
        device.close()
