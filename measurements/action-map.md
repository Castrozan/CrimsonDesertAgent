# Game action map

Which game actions the plugin can perform, and how far each is proven in the running game. Status values: `proven`
(repeated live with a measured result), `partial` (worked live, not repeatable or not fully measured), `known` (the
control is known, no engine step and no measurement), `unmapped` (control or mechanism unknown).

Last updated 2026-11-17, at `b83cefc`.

## Movement and camera

| Action | Control or step | Status | Evidence or gap |
| --- | --- | --- | --- |
| Walk and run to a point | `goto X Z` | proven | Closed loop, detours on `stuck` with three sidesteps |
| Turn the camera to a heading | `turn DEGREES` | proven | Within 3 degrees |
| Walk to the quest marker | `marker` | proven | 19 m in two legs, triggered the cutscene |
| Approach an actor | `approach KEY_OR_NAME` | proven | Reports `talk_prompt`, never aborts the script |
| Sprint | `a` held while moving | known | Speed gain never measured |
| Crouch | `left_stick_click` | known | Stance is not in the bridge state; needs a screenshot |
| Jump | tap `x` | proven | 0.4 m |
| Precision jump | hold `x` 1 s while moving | proven | Crosses the corridor gap and waist-high steps |
| Mount a low wall | tap `x` at the wall | proven | Corridor of the Void low wall |
| Cling and climb a tall wall | `climb` | partial | Reached 9.3 m twice before a relaunch; 3.8 to 6.4 m in seven tries after |
| Move sideways while clinging | left stick on the wall | unmapped | Tutorial names it; never tried |
| Stamina reading | none | unmapped | Not in the bridge state, not read by `hud` |
| Swim, dive | none | unmapped | The player only fell into water |
| Mount, ride | none | unmapped | Not reached in the story |
| Glide, grapple, other traversal | none | unmapped | Not reached in the story |
| Lock the camera on a target | d-pad | unmapped | Direction unknown; `fight` aims with the right stick instead |

## Combat

| Action | Control or step | Status | Evidence or gap |
| --- | --- | --- | --- |
| Light attack | `rb` | proven | Hashes `DE17B004`, `BDB85277`, `041E61FB` for the three-hit chain |
| Hold ground and fight | `fight X Z seconds= leash=` | proven | Won In Ashes in three rounds; 51 to 60 strikes per 45 s |
| Heavy attack | `rt` | known | No hash recorded |
| Guard | `lb` | partial | Used by `fight` after a hit; damage reduction not measured |
| Dodge | `b` | known | Not used by `fight`; no measurement |
| Punch, kick | `y` | known | No hash recorded |
| Draw or stow the weapon | first `rb` draws | partial | Draw hashes `8F384208`, `2C36F9CE`; stow control unknown |
| Quick time event | button shown on screen | unmapped | `hud` cannot read the glyph; needs glyph detection |
| Skills, special attacks | none | unmapped | Not explored |
| Ranged attack, aim | none | unmapped | Not explored |
| Avoid fire | hazard memory | partial | Counts fall damage as fire; ignores fire while an enemy is within 3 m |
| Revive at checkpoint | `hold 1.2 x` | proven | Used after each death |
| Heal, use an item | none | unmapped | Item wheel and consumables unknown |

## Story and interaction

| Action | Control or step | Status | Evidence or gap |
| --- | --- | --- | --- |
| Read quest, guide, prompt, speech | `hud` | proven | 0.85 to 1.4 s; misses top-left tutorial text |
| Talk to a character | `talk KEY_OR_NAME` | partial | Hold `x` 1 s started a dialogue by hand; the step never met a talkable character |
| Sit through a cutscene | `hud; wait 4` loop, no presses | proven | About 100 s without input, quest advanced |
| Advance a tutorial page | `rb` on a `Next` prompt | partial | Seen once |
| Refuse the exit prompt | confirm guard | proven | Engine refuses `a` and `start` on exit words |
| Pick up, loot, interact with objects | none | unmapped | Prompt text is read; the control was never exercised |
| Open the map, set a waypoint | none | unmapped | Only the minimap is read |
| Inventory, equipment, skill menus | `start` | unmapped | Menus were never navigated |
| Save, rest, fast travel | none | unmapped | Not explored |
| Read the pause state | bridge `paused` | known | Deployed in the mod; the confirm guard reads it, `hud` does not report it |

## Mod development loop

| Action | Control or step | Status | Evidence or gap |
| --- | --- | --- | --- |
| Launch or attach | `mod launch` | proven | Ends with the player in the world |
| Build, deploy, relaunch | `mod cycle` | partial | Each stage ran; never end to end in one job |
| Peer staging and comparison | `peer` scripts | proven | See `2026-11-16-two-agents.md` |
| Identify an action by packet hash | `packets`, `prove_attack` | partial | `prove_attack` baseline is polluted by earlier attacks |
