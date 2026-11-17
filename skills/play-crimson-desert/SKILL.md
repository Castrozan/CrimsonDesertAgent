---
name: play-crimson-desert
description: Play Crimson Desert through the crimson-desert MCP tools - observe structured state, send timed pad scripts, steer camera and character in closed loop. Use for any in-game task - moving, fighting, menus, or scripted input sequences.
---

### One script per decision

Every tool call costs a model turn, so the loop is as fast as the calls are few. Put a whole intention into one
`run_script` call: observe, act, observe again, as in `focus; state; turn 90; goto -9840 -2800 rb; press rt; state`.
The `run_script` tool description holds the step grammar and the control names; do not guess a step.

Start each script with `focus`: input reaches the game only while its window has focus, and it silently does nothing
otherwise. Everything is released when a script ends, fails or is aborted, so nothing stays held between calls.

Without the MCP server, run the same script text through the plugin's `scripts/crimson-desert run`.

### Reading the answer

Each step reports its duration in `ms`; `state`, `turn`, `goto`, `log` and `shot` add a `result`. On `ok: false` the
`error` names the failing step and the steps after it did not run. An invalid step rejects the whole script before any
input is sent.

### Overlapping inputs

`down`, `up` and `stick` return at once; `wait` and `press` between them build any timeline, such as a guard held
through two attacks then a dodge forward: `down lt; wait 0.2; press rb; press rb; up lt; stick left 0 1; press b`.

### Closed loop over dead reckoning

Prefer `turn` and `goto` to timed `look` and `move`: they correct the stick from live state 50 times a second, so
slopes, camera drift and collisions do not make them miss. Heading is degrees from +Z toward +X; to face a point use
`atan2(target_x - x, target_z - z)`.

Read their `result`. `arrived: false` comes with `timeout`, `stuck` (an obstacle or blocked movement) or
`not in world`. On `stuck`, sidestep or jump and retry; repeating the same `goto` fails the same way.

### Know the status before acting

Begin a task with `focus; status`: it adds ground speed, whether the game window has focus, and what the pad holds to
the `state` fields. Use `state` inside a sequence, where its 1 ms cost matters, and `status` at decision points.

State carries every field the running mod exposes, so read what it returns before assuming a gap. Anything absent
from it, such as stance, menus, prompts or dialogue on older mod builds, needs the `screenshot` tool, or `shot PATH`
inside a script when the picture must be taken at an exact moment. When stance is absent, take a screenshot before
the first action: a crouched character moves at walking pace under every input.

### Controls

Default pad layout: `rb` light attack, `rt` heavy attack, `lb` guard, `b` dodge, `x` jump, `a` sprint while moving
and confirm in menus, `start` menu, `left_stick_click` toggles crouch. Both sticks ignore deflections under 0.3.

When input seems ignored, check in order: 1) the window lost focus; 2) a menu or dialogue is open; 3) the world is
still streaming after a load, which blocks movement for a while. Probe with `state; move 0 1 0.5; state` and compare
positions.

`abort` stops a running script from a second call and releases the pad.
