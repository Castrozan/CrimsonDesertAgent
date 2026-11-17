---
name: play-crimson-desert
description: Play Crimson Desert through the crimson-desert MCP tools - observe structured state, send timed pad scripts, steer camera and character in closed loop. Use for any in-game task - moving, fighting, menus, or scripted input sequences.
---

### One script per decision

Every tool call costs a model turn, so the loop is as fast as the calls are few. Put a whole intention into one
`run_script` call: observe, act, observe again, as in `focus; hud; status; goto -9840 -2800 a; hud`.
The `run_script` tool description holds the step grammar and the control names; do not guess a step.

Start each script with `focus`: input reaches the game only while its window has focus, and it silently does nothing
otherwise. Everything is released when a script ends, fails or is aborted, so nothing stays held between calls.

Without the MCP server, run the same script text through the plugin's `scripts/crimson-desert run`.

### Reading the answer

Each step reports its duration in `ms`; observing and steering steps add a `result`. On `ok: false` the
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

### Follow the story from text, not pictures

`hud` returns the screen as fields: `quest`, `objectives`, `guide` (the current instruction), `prompt`, `speech`
(subtitles, speaker first), `marker_m` and `marker_bearing_degrees` for the quest marker on the minimap, and `other`
text with window positions. Begin every story decision with `focus; hud; status` and do what `guide` says.

The quest marker is the target. `marker` walks to it in legs, re-reading the minimap each leg and sidestepping
obstacles; follow it with `hud; status`. Progress is the `guide`, `quest` or `objectives` text changing, and often
only `guide` changes.

To speak with someone use `talk KEY_OR_NAME`: it approaches, holds the talk button, then waits without pressing until
the conversation ends, and returns the speaker, the lines spoken, and the quest and guide text before and after.
`approach` alone reports `talk_prompt` and any name it read; `status` then lists that actor with `name` and `talked`.

When `hud` returns `quest: null`, a cutscene, dialogue or tutorial is playing. Press nothing: loop `hud; wait 4` and
read `speech` until `quest` returns. Holding or repeating `a` there skips into prompts that can end the game. Press
`a` once only when `prompt` is `Next` on three reads in a row.

Never hold an attack button while walking. Take a screenshot only when `hud` gives nothing useful, such as for a map.

### Proving an attack

`prove_attack rb` presses the control, waits for the packet recording to flush, and returns the action hashes that
were absent from the 30 seconds before it. Idle for a few seconds first so the baseline is quiet, then pair it with
`press rb 0.1 0; shot PATH burst=6 every=0.1` in one script for the picture.

### Never confirm an exit

A stray `b`, `start` or window close can raise the game's exit prompt, and the next `a` confirms it and ends the
game. The engine refuses `a` and `start` when the last `hud` shows exit, quit or title words, and while the game is
paused unless `hud` was read in the same script since the last confirm. On `exit_prompt: true` press `b`, then `hud`.

### Fighting and dying

Fight with the `fight` step, not hand-timed presses: `fight X Z seconds=45 leash=8` holds the ground around X Z, keeps
one target, turns the camera onto it, strikes in three-hit combos when aimed and in reach, guards after a hit, and
never lunges toward a recorded fire. Its result counts strikes and damage. Anchor it on the quest marker's
`marker_position`, then read `hud; status` and repeat until the objective counter moves.

When `hud` shows `Revive at Checkpoint`, run `hold 1.2 x`, wait twelve seconds and read `hud` again; `a` does nothing
on that screen. A lone button glyph in the middle of the screen is a quick time prompt that `hud` cannot read: take
a screenshot when health drops with no clear cause, and press the button shown.

### Traversal

Tutorial text appears in the top left corner, where `hud` does not read: screenshot it when the guide names a move
you do not know. A tap of `x` jumps 0.4 m. Holding `x` for one second while pushing forward makes the long precision
jump that crosses gaps and mounts waist-high steps. Next to a wall, a tap of `x` climbs it; jump while tilting the
stick toward a tall wall to cling, then steer along it. Clinging works by walking into the wall, then `stick left 0 1; press x 0.15 0` and keeping the
stick toward the wall: height rises about 0.7 m per second and the player goes over the top. Face the wall squarely
first with `turn`. Falling into the void respawns the player before the obstacle. Track `position` after each attempt: the height component tells whether a climb worked.

### Fire and other ground hazards

`goto`, `approach`, `talk` and `marker` stop when health falls with no enemy within three metres, walk back to the last
safe spot, and record the place; `status` lists these as `fire_hazards`, and later walks route around them or refuse
a target inside one. A result whose reason starts with `burning` means the way ahead burns: pick another direction.
Timed `move` and attack lunges are not protected, so never `move` or attack toward a listed hazard or a visible fire.

### Controls

Default pad layout: `rb` light attack, `rt` heavy attack, `lb` guard, `b` dodge, `x` jump, `a` sprint while moving
and confirm in menus, `start` menu, `left_stick_click` toggles crouch. Both sticks ignore deflections under 0.3.

When input seems ignored, check in order: 1) the window lost focus; 2) a menu or dialogue is open; 3) the world is
still streaming after a load, which blocks movement for a while. Probe with `state; move 0 1 0.5; state` and compare
positions.

`abort` stops a running script from a second call and releases the pad.
