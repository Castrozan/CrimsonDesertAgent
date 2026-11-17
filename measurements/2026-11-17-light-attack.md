# Light attack, isolated

Measured on 2026-11-17 in quest "In Ashes" at the checkpoint near (-9960.2, 618.7, -2897.6), with no character within
3.9 m and health constant at 300. Each `press rb 0.1 0` was preceded and followed by nine or more seconds without input.

The idle player emits StartAction `B77A7FDD / DF773D35` about every 1.3 s. Each light attack press produced, in order,
`DE17B004 / DF773D35`, then `BDB85277 / DF773D35` 1.8 s later, then `041E61FB / DF773D35` 1.3 s after that, and the
idle action resumed. The player moved about 2 m forward on the first of the three. Three presses gave this sequence
three times.

The first press after a revive, with the weapon stowed, gave `8F384208 / 26107D3C` and `2C36F9CE / 26107D3C` instead.
`450ADC56` followed one later press and one heavy attack press and is not identified.

`light-attack-burst.jpg` holds seven frames over 0.8 s from the press: the shield arm comes round in the last three.

`prove_attack` reported these presses as proven, but its idle window takes in earlier attacks, so its list of new
hashes was not what identified the action; the timeline from `start_actions` was.
