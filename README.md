# CrimsonDesertAgent

A Claude Code plugin that lets an agent session play Crimson Desert: it reads structured game state, drives a virtual
Xbox 360 pad with timed input scripts, and steers the camera and the character in closed loop.

## Install

```
/plugin marketplace add Castrozan/CrimsonDesertAgent
/plugin install crimson-desert-agent@crimson-desert-agent
```

The plugin brings an MCP server (`crimson-desert`), two skills (`play-crimson-desert`, `launch-crimson-desert`) and
the scripts in `scripts/`. The Python environment is built on first use, with `nix` when present and a `venv`
otherwise.

## Requirements

- Linux with Hyprland: `hyprctl` focuses the game window and `grim` takes screenshots.
- Write access to `/dev/uinput` for the virtual pad.
- Crimson Desert on Steam with Proton, running the
  [CrimsonDesertMultiplayer](https://github.com/Castrozan/CrimsonDesertMultiplayer) mod `cdmp.asi` with its agent
  bridge enabled. The bridge serves game state as JSON on a loopback TCP port.

## How it works

One input daemon owns the virtual pad and runs scripts; the MCP server and the command line are thin clients of its
unix socket. The pad therefore survives across calls and sessions, and a whole sequence of inputs and observations
costs one round trip. Step timing follows a deadline schedule, so durations do not drift across a script.

The script language is printed by `scripts/crimson-desert` with no arguments and is part of the `run_script` tool
description.

## Environment overrides

| Variable | Meaning |
| --- | --- |
| `CRIMSON_DESERT_BIN64` | Game `bin64` directory, where the mod writes `cdmp.log` |
| `CRIMSON_DESERT_BRIDGE_PORT` | Loopback port of the state bridge |
| `CRIMSON_DESERT_STEAM_APPLICATION` | Steam application id used to launch |
| `CRIMSON_DESERT_SHADER_DIALOG_SKIP_POINT` | Screen point clicked to skip Steam's shader dialog |
| `CRIMSON_DESERT_WORLD_TIMEOUT_SECONDS` | How long the launcher waits for the world |

## Development

`scripts/run-tests` runs the unit tests. `scripts/crimson-desert measure` times scripted sequences against a running
game; recorded runs live in `measurements/`.
