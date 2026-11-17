import glob
import os
import struct
from dataclasses import asdict, dataclass

FILE_HEADER_BYTES = 12
RECORD_HEADER = struct.Struct("<QBBHHHII")
PACKET_HEADER = struct.Struct("<HbH")
START_ACTION_REQUEST = 2431
START_ACTION_BYTES = 729
SECOND_HASH_OFFSET = 0x49
POSITION_OFFSET = 0x8E + 0xC0
PLAYER_KEY_PREFIX = 0xA0


@dataclass(frozen=True)
class StartAction:
    seconds: float
    key: str
    first_hash: str
    second_hash: str
    position: list[float]
    flag: int


def newest_recording(directory: str) -> str | None:
    recordings = sorted(glob.glob(os.path.join(directory, "cdmp_packets_*.bin")))
    return recordings[-1] if recordings else None


def start_actions(data: bytes, players_only: bool = True) -> list[StartAction]:
    position = FILE_HEADER_BYTES
    first_time = None
    actions = []
    while position + RECORD_HEADER.size <= len(data):
        time_microseconds, _, _, _, copied, _, _, _ = RECORD_HEADER.unpack_from(
            data, position
        )
        position += RECORD_HEADER.size
        packet = data[position : position + copied]
        position += copied
        if len(packet) < PACKET_HEADER.size:
            continue
        if first_time is None:
            first_time = time_microseconds
        opcode, _, _ = PACKET_HEADER.unpack_from(packet, 0)
        payload = packet[PACKET_HEADER.size :]
        if opcode != START_ACTION_REQUEST or len(payload) < START_ACTION_BYTES:
            continue
        key, first_hash = struct.unpack_from("<II", payload, 0)
        if players_only and key >> 24 != PLAYER_KEY_PREFIX:
            continue
        (second_hash,) = struct.unpack_from("<I", payload, SECOND_HASH_OFFSET)
        x, y, z = struct.unpack_from("<3f", payload, POSITION_OFFSET)
        actions.append(
            StartAction(
                round((time_microseconds - first_time) / 1e6, 2),
                f"{key:08X}",
                f"{first_hash:08X}",
                f"{second_hash:08X}",
                [round(x, 2), round(y, 2), round(z, 2)],
                payload[START_ACTION_BYTES - 1],
            )
        )
    return actions


def read_start_actions(directory: str, path: str | None, last: int) -> dict:
    recording = path or newest_recording(directory)
    if recording is None or not os.path.exists(recording):
        return {"ok": False, "error": f"no packet recording found in {directory}"}
    with open(recording, "rb") as recording_file:
        actions = start_actions(recording_file.read())
    return {
        "ok": True,
        "recording": recording,
        "count": len(actions),
        "start_actions": [asdict(action) for action in actions[-last:]],
    }
