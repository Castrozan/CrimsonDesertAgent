---
name: develop-crimson-desert-mod
description: Develop and verify the Crimson Desert co-op mod with the crimson-desert tools - build, deploy, relaunch, stage the peer, take full-resolution or burst screenshots, read the mod log and packet recordings. Use for any change to cdmp.asi or cdmp_peer that must be proven in the running game.
---

### One tool per step of the loop

Every step of build, deploy, relaunch, stage and verify is an MCP tool or a subcommand of the plugin's
`scripts/crimson-desert`; both share one engine. Do not hand-write socket, `grim`, image or launch glue: when a step
is missing, add it to the plugin.

### The game lock comes first

The game is shared. `game_lock` with action `take` succeeds only when nobody holds the lock; release it when done.
`mod_loop` refuses every action that restarts the game unless `holder` names the current holder. Input and peer
commands are not checked by code: send them only while you hold the lock.

### Build, deploy, relaunch

`mod_loop` runs detached and returns at once; poll action `status` until `running` is false and read `outcome`.
`cycle` builds the mod, copies `cdmp.asi` into the game and relaunches until the player is in the world;
`deploy-relaunch` skips the build, `relaunch` keeps the deployed mod, `launch` attaches or starts without stopping
anything. A relaunch costs minutes, so batch changes before one.

After a relaunch the peer must be taught again: run `peer_process` with `restart`, then the player step `teach`,
which walks the player until the peer reports it can move and animate.

### Stage what you want to see

In `run_peer_script`, `stage ahead=2.5 from=-2.5 to=3 speed=1.2` places the peer body ahead of the player's camera,
to its left, and walks it across the view. `compare` returns the distance between the peer body and the copy the
player's game shows, which is the number to quote for position sync.

### Look at it

`shot` defaults to half resolution for cheap checks. To judge a pose use `scale=1` with `actor=coop_copy`, which
crops around the peer's copy; add `brightness=1.8` at night and `burst=4 every=0.25` to see motion as frames side by
side. Combine staging and a burst by starting the walk, then taking the burst in the next call.

When the crop misses the actor, the camera's field of view differs from the default: pass `fov=DEGREES`, or use
`crop=LEFT,TOP,WIDTH,HEIGHT` in window pixels.

### Read what the mod recorded

`read_game_log` returns the last lines of this launch's mod log, filtered by a regular expression. `start_actions`
lists the player's StartAction requests from the newest packet recording with time, both action hashes and position,
which is how an animation or attack is identified.
