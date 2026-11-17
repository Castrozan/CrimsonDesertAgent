---
name: play-crimson-desert-peer
description: Play the co-op peer in Crimson Desert - the second character that another agent's player sees - through the crimson-desert run_peer_script tool. Use when asked to be the peer, the partner, or the second player, independently of the agent driving the player.
---

### The peer has no pad and no window

The peer is a body inside the co-op stand-in `cdmp_peer` running in agent mode, not a second game. Drive it only with
`run_peer_script`; `run_script`, `abort` and the pad belong to the agent playing the player, and using them moves
that agent's character.

### Ask the peer what it accepts

The control port defines the commands and they grow with the mod. Send `help` first and use what it lists; do not
assume a command from the player's script language. An unreachable port means `cdmp_peer` is not running in agent
mode.

### One script per decision

Put a whole intention into one call, as with the player: commands separated by `;` go out in order over one
connection, `wait SECONDS` pauses between them, and each answer returns with its timing. End a script with the peer's
state command so the answer shows where the body ended up.

### See through the player's bridge

`get_state` reads the player's game, which is the world the peer body appears in: use it to find the player and, when
the mod lists nearby actors, to place the peer relative to them. `screenshot` shows the player's view, so it proves
what the peer looks like from outside.
