# Two agents at once, 2026-11-16

Same machine and game as the end-to-end run. The mod (`cdmp` at `bdeb9f4`) served velocity and up to 16 nearby actors
on the state bridge, and `cdmp_peer` ran in agent mode with its UDP control port.

Two fresh `claude -p` sessions started at the same moment, each with only this plugin: one told to play the player,
one told to play the peer. Neither knew the other's plan.

## Player agent

Wall time 17.3 s, two `run_script` calls.

| Step | Time ms | Result |
| --- | --- | --- |
| `turn 20 tolerance=2 timeout=5` | 751 | camera heading 57 to 19 degrees |
| `goto -9883.35 -2808.46 tolerance=1 timeout=10` | 4770 | arrived 0.98 m from the target, from (-9886.77, -2817.86) |
| `shot` | 208 | saved |

## Peer agent

Wall time 33.9 s, five `run_peer_script` calls after `help`. Task: reach a point within 4 m of the player, face them,
and follow until the player stops.

| Script | Time ms | Result |
| --- | --- | --- |
| `state` | 0.5 | player seen moving at (-9886.3, -2816.7) |
| `goto -9883.0 -2814.5; wait 1; face 236; wait 0.5; state` | 1502 | body at the point; player had moved on, 5.65 m away |
| `state; wait 1; state` | 1004 | player position unchanged: stopped |
| `goto -9883.31 -2811.94; wait 1.5; face 356; wait 0.3; state` | 1803 | body at (-9883.30, -2812.08), yaw 356 |

The player's bridge then listed the `coop_copy` actor at (-9883.30, 620.28, -2812.08), 3.14 m from the player, and the
screenshot showed the peer's nameplate at 3 m.

## Notes

A peer command round trip is 0.4 to 3 ms. With 16 actors in the answer a bridge state read rose from about 1 ms to
15 to 60 ms. The peer body slides without a walk animation and takes its height from the player.
