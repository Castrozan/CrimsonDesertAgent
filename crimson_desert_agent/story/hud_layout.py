import math
import re

REFERENCE_HEIGHT = 1080.0
LEFT_COLUMN = (0.0, 0.45, 0.30, 0.76)
DATE_LINE = re.compile(r"^Day \d+")
MINIMAP_BLOCK = (0.0, 0.76, 0.18, 1.0)
GUIDE_BLOCK = (0.15, 0.90, 0.85, 1.0)
SPEECH_BLOCK = (0.15, 0.72, 0.85, 0.90)
MINIMAP_PIXELS_PER_METRE = 3.2
MINIMAP_CENTRE = (155.0, 944.0)
LABEL_CENTRE = (17.0, 8.0)
EDGE_DISTANCE = re.compile(r"^([0-9lO]{1,4})m$")
PROMPT_ACTIONS = (
    "Talk",
    "Next",
    "Skip",
    "Interact",
    "Pick",
    "Open",
    "Mount",
    "Confirm",
    "Close",
)
EXIT_WORDS = ("exit", "quit", "title")
PEER_LABEL = re.compile(r"cdmp|relay|Xbox 360 Controller")
PEER_DISTANCE_REACH = 90


def inside(line: dict, block: tuple, width: int, height: int) -> bool:
    left, top, right, bottom = block
    scale = height / REFERENCE_HEIGHT
    return left * REFERENCE_HEIGHT * 16 / 9 * scale <= line[
        "x"
    ] < right * REFERENCE_HEIGHT * 16 / 9 * scale and (
        top * height <= line["y"] < bottom * height
    )


def marker_metres(marker: dict) -> int:
    if marker["metres"] is not None:
        return marker["metres"]
    return round(math.hypot(marker["right"], marker["down"]) / MINIMAP_PIXELS_PER_METRE)


def marker_bearing(marker: dict, camera_heading_degrees: float) -> float:
    return round(
        (
            camera_heading_degrees
            + math.degrees(math.atan2(marker["right"], -marker["down"]))
        )
        % 360.0,
        1,
    )


def near_peer_label(line: dict, peer_labels: list[dict]) -> bool:
    return any(
        abs(line["x"] - label["x"]) <= PEER_DISTANCE_REACH * 2
        and 0 <= line["y"] - label["y"] <= PEER_DISTANCE_REACH
        for label in peer_labels
    )


def prompt_in(lines: list[dict]) -> dict | None:
    for line in lines:
        for action in PROMPT_ACTIONS:
            if action in line["text"].split():
                return {
                    "action": action,
                    "text": line["text"],
                    "x": line["x"],
                    "y": line["y"],
                }
    return None


def marker_from_label(lines: list[dict], width: int, height: int) -> dict | None:
    scale = height / REFERENCE_HEIGHT
    for line in lines:
        match = EDGE_DISTANCE.match(line["text"].replace(" ", ""))
        if match and inside(line, MINIMAP_BLOCK, width, height):
            return {
                "right": line["x"] / scale + LABEL_CENTRE[0] - MINIMAP_CENTRE[0],
                "down": line["y"] / scale + LABEL_CENTRE[1] - MINIMAP_CENTRE[1],
                "metres": int(match.group(1).replace("l", "1").replace("O", "0")),
            }
    return None


def describe(
    lines: list[dict], frame_size: tuple[int, int], state: dict, marker: dict | None
) -> dict:
    width, height = frame_size
    marker = marker or marker_from_label(lines, width, height)
    peer_labels = [line for line in lines if PEER_LABEL.search(line["text"])]
    lines = [
        line
        for line in lines
        if line not in peer_labels and not near_peer_label(line, peer_labels)
    ]
    column = [
        line["text"] for line in lines if inside(line, LEFT_COLUMN, width, height)
    ]
    date_row = next(
        (index for index, text in enumerate(column) if DATE_LINE.match(text)),
        len(column),
    )
    quest, place = column[:date_row], column[date_row:]
    guides = [
        line["text"] for line in lines if inside(line, GUIDE_BLOCK, width, height)
    ]
    placed = (LEFT_COLUMN, MINIMAP_BLOCK, GUIDE_BLOCK, SPEECH_BLOCK)
    report = {
        "quest": quest[0] if quest else None,
        "objectives": quest[1:],
        "guide": guides[-1] if guides else None,
        "prompt": prompt_in(lines),
        "speech": [
            line["text"] for line in lines if inside(line, SPEECH_BLOCK, width, height)
        ],
        "marker_m": marker_metres(marker) if marker else None,
        "marker_bearing_degrees": None,
        "place": place,
        "other": [
            line
            for line in lines
            if not any(inside(line, block, width, height) for block in placed)
        ],
        "exit_prompt": any(
            word in line["text"].lower().split()
            for line in lines
            for word in EXIT_WORDS
        ),
    }
    heading = state.get("camera_heading_degrees")
    if marker and heading is not None:
        report["marker_bearing_degrees"] = marker_bearing(marker, heading)
        position = state.get("position")
        if position:
            bearing = math.radians(report["marker_bearing_degrees"])
            report["marker_position"] = [
                round(position[0] + marker_metres(marker) * math.sin(bearing), 1),
                round(position[2] + marker_metres(marker) * math.cos(bearing), 1),
            ]
    return report
