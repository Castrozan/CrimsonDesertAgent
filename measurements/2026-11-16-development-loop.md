# Mod development loop, 2026-11-16

Each step of the co-op mod's develop-and-verify loop run once through the plugin against the live game
(mod `cdmp` at `b363941`, agent peer under Wine).

| Step | Command | Result |
| --- | --- | --- |
| Full-resolution shot | `shot PATH scale=1` | 1600x900 of the game window only, 147 ms |
| Pixel crop | `shot PATH crop=0,0,600,160 scale=1` | 600x160, 58 ms |
| Crop around an actor | `shot PATH actor=coop_copy size=500 scale=1 brightness=1.8` | peer nameplate centred in the crop, 96 ms |
| Burst | `shot PATH burst=6 every=0.25 actor=coop_copy size=300 scale=1 brightness=2.4` | six frames side by side, 1771 ms, [image](peer-walk-burst.jpg) |
| Stage the peer | `peer "stage ahead=10 from=1 to=6 speed=1.2"` | teleported, then walked across the view, 26 ms to issue |
| Compare peer and copy | `peer "compare"` | ground error 0.0 m, height error 0.0 m, standing and after a walk |
| Peer lifecycle | `peer-process restart` | stopped, started, returned once the body was placed |
| Teach the peer | `teach timeout=25` | returned at once: the restarted peer already had its move template |
| Build, deploy, relaunch | `mod cycle`, then `mod launch` | see below |
| Mod log | `log --grep "Agent bridge: listening" --lines 2` | the matching line of this launch |
| Packet recording | `packets --last 3` | 287 player StartActions listed with time, both hashes and position |
| Game lock | `lock take`, `mod relaunch` without it | taken when free; relaunch refused while another name held it |

## Build, deploy, relaunch

`mod cycle` rebuilt the mod (one object, relinked `cdmp.asi`), stopped the game, deployed, started it through Steam and
skipped the shader-cache dialog with a click from a virtual pointer; Steam logged the response `skip` two seconds
after the dialog appeared. The job then stopped with "the game process is not running": it allowed the process 20 s
to appear and the launch wrapper needed longer. The grace is now 120 s. `mod launch` attached to the starting game,
pressed through the title and reported `in world` 91 s later, 2 min 46 s after the game was stopped. The corrected
`cycle` has not been run end to end since the fix.

## State read cost

With the mod caching its actor list, 30 consecutive `state` steps with 16 actors in range took 8.3 ms minimum,
10.5 ms median, 25.1 ms maximum. Before the cache the same read took 15 to 60 ms; without actors it took about 1 ms.

## Does the copy's walk animate

Yes. In the [burst](peer-walk-burst.jpg) the copy under the `agent peer` nameplate crosses the trail left to right and
its legs change pose from frame to frame: together, striding with the knee bent, together again.

## Not exercised

`teach` had nothing to teach, so its walking loop is covered by a unit test only. The peer state no longer reports
`knows_walk_animation`; `teach` treats an absent lesson as learnt.
