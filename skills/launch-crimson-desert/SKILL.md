---
name: launch-crimson-desert
description: Launch Crimson Desert or attach to a running game and wait until the player is in the world. Use before playing, when the state bridge is unreachable, or when the game must be restarted.
---

### Attach before launching

Run the plugin's `scripts/crimson-desert state` first: it prints the game state as one JSON line without touching the
pad. `"in_world": true` means play now. An unreachable bridge means the game is not running, is still starting, or
runs without the `cdmp.asi` mod and its `[agent] enabled=1` bridge.

### Launch

Back up the save directory before a launch that will load a save.

The plugin's `scripts/launch-game` attaches when the player is already in the world; otherwise it starts the game
through Steam, skips the shader-cache dialog, taps through the title screens and prints `in world`. `--restart` stops
a running game first. A launch takes minutes: start it detached with its output in a file and poll that file, because
a blocking call outlives the tool timeout.

After a load the world keeps streaming and movement can be blocked for a while. Probe with
`state; move 0 1 0.5; state` and compare positions before real work.

### Requirements

Linux with Hyprland (`hyprctl`, `grim`), write access to `/dev/uinput`, Steam with Proton, and `nix` or `python3`
with `venv` for the Python environment built on first use. The README lists the environment overrides.
