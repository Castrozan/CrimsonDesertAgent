import math
import os
import struct
import tempfile
import unittest
from unittest import mock

from hypothesis import strategies as st

from crimson_desert_agent.development import game_lock
from crimson_desert_agent.development.packet_recording import (
    FILE_HEADER_BYTES,
    PACKET_HEADER,
    POSITION_OFFSET,
    RECORD_HEADER,
    SECOND_HASH_OFFSET,
    START_ACTION_BYTES,
    START_ACTION_REQUEST,
    read_start_actions,
    start_actions,
)

angles = st.floats(min_value=0, max_value=2 * math.pi, allow_nan=False)
metres = st.floats(min_value=-30, max_value=30, allow_nan=False)


def record(time_microseconds: int, opcode: int, payload: bytes) -> bytes:
    packet = PACKET_HEADER.pack(opcode, 0, len(payload)) + payload
    return (
        RECORD_HEADER.pack(time_microseconds, 0, 0, len(packet), len(packet), 0, 1, 1)
        + packet
    )


def start_action(
    key: int, first_hash: int, second_hash: int, position: tuple[float, float, float]
) -> bytes:
    payload = bytearray(START_ACTION_BYTES)
    struct.pack_into("<II", payload, 0, key, first_hash)
    struct.pack_into("<I", payload, SECOND_HASH_OFFSET, second_hash)
    struct.pack_into("<3f", payload, POSITION_OFFSET, *position)
    payload[-1] = 1
    return bytes(payload)


class PacketRecordingTest(unittest.TestCase):
    def test_lists_only_the_players_start_actions_with_time_hashes_and_position(self):
        data = (
            bytes(FILE_HEADER_BYTES)
            + record(1_000_000, 7, b"other")
            + record(
                3_500_000,
                START_ACTION_REQUEST,
                start_action(0xA0100001, 0xECF9B7D2, 0x26107D3C, (1.5, 2.0, -3.25)),
            )
            + record(
                4_000_000,
                START_ACTION_REQUEST,
                start_action(0xB0100001, 1, 2, (0, 0, 0)),
            )
            + record(5_000_000, START_ACTION_REQUEST, b"short")
            + b"\x01\x02"
        )
        actions = start_actions(data)
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            (
                actions[0].seconds,
                actions[0].key,
                actions[0].first_hash,
                actions[0].second_hash,
                actions[0].position,
                actions[0].flag,
            ),
            (2.5, "A0100001", "ECF9B7D2", "26107D3C", [1.5, 2.0, -3.25], 1),
        )
        self.assertEqual(len(start_actions(data, players_only=False)), 2)

    def test_reads_the_newest_recording_and_reports_a_missing_one(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(read_start_actions(directory, None, 5)["ok"])
            for name in (
                "cdmp_packets_20260101-000000.bin",
                "cdmp_packets_20260102-000000.bin",
            ):
                with open(os.path.join(directory, name), "wb") as recording:
                    recording.write(bytes(FILE_HEADER_BYTES))
            self.assertTrue(
                read_start_actions(directory, None, 5)["recording"].endswith(
                    "20260102-000000.bin"
                )
            )


class GameLockTest(unittest.TestCase):
    def test_only_the_holder_passes_and_only_an_absent_lock_can_be_taken(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(
                game_lock, "GAME_LOCK_PATH", os.path.join(directory, "game.lock")
            ):
                self.assertIsNone(game_lock.holder())
                for name in ("Qin Shi Huang", "", None):
                    with self.assertRaises(game_lock.LockRefused):
                        game_lock.require(name)
                game_lock.take("Tamamo Cat", "22:42:35")
                self.assertEqual(game_lock.holder(), "Tamamo Cat 22:42:35")
                game_lock.require("Tamamo Cat")
                game_lock.take("Tamamo Cat", "23:00:00")
                for refused in (
                    lambda: game_lock.take("Qin Shi Huang", "23:00:00"),
                    lambda: game_lock.require("Tamamo"),
                    lambda: game_lock.release("Qin Shi Huang"),
                ):
                    with self.assertRaises(game_lock.LockRefused):
                        refused()
                game_lock.release("Tamamo Cat")
                self.assertIsNone(game_lock.holder())
                game_lock.release("Anyone")


if __name__ == "__main__":
    unittest.main()
