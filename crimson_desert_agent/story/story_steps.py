from ..scripting.observation import ActorNotListed, listed_actor
from .acquaintances import Acquaintances, name_in
from .attack_proof import DEFAULT_FLUSH_SECONDS, prove
from .combat import hold_ground
from .conversation import DEFAULT_TIMEOUT_SECONDS, converse
from .detour import go_around
from .hud_reading import read_hud

APPROACH_STANDOFF_M = 2.0
TALK_STANDOFF_M = 1.3
WALK_TIMEOUT_SECONDS = 30.0
MARKER_ARRIVAL_M = 4
MARKER_LEG_M = 12.0
MARKER_LEGS = 8
VERBS = ("hud", "approach", "talk", "marker", "prove_attack", "fight")


class StorySteps:
    def __init__(
        self,
        devices,
        bridge,
        steering,
        pause,
        clock,
        acquaintances: Acquaintances,
        hazards=None,
    ) -> None:
        self._devices = devices
        self._bridge = bridge
        self._steering = steering
        self._pause = pause
        self._clock = clock
        self._people = acquaintances
        self._hazards = hazards
        self.last_hud: dict | None = None

    def hud(self, step=None) -> dict:
        crop = step.options.get("crop") if step else None
        self.last_hud = read_hud(
            self._devices.camera,
            self._devices.read_words,
            self._devices.read_marker,
            self._bridge.read_state,
            crop,
        )
        return self.last_hud

    def _walk(self, x: float, z: float, tolerance: float, timeout: float) -> dict:
        return go_around(self._steering, x, z, tolerance, timeout, self._hazards)

    def approach(self, step, standoff: float = APPROACH_STANDOFF_M) -> dict:
        key = self._people.key_for(step.values[0])
        try:
            actor = listed_actor(self._bridge.read_state(), key)
        except ActorNotListed:
            return {"skipped": "actor gone", "actor": step.values[0]}
        reached = self._steering.approach(
            actor["position"],
            step.options.get("distance", standoff),
            step.options.get("timeout", WALK_TIMEOUT_SECONDS),
            self._walk,
        )
        seen = self.hud()
        prompt = seen["prompt"]
        name = name_in([line["text"] for line in seen["other"]])
        self._people.learn(actor["key"], name)
        return {
            **reached,
            "key": actor["key"],
            "name": name,
            "talk_prompt": bool(prompt and prompt["action"] == "Talk"),
        }

    def talk(self, step) -> dict:
        reached = self.approach(step, TALK_STANDOFF_M)
        if "skipped" in reached:
            return reached
        spoken = converse(
            self._devices.pad,
            self.hud,
            self._bridge.read_state,
            self._pause,
            self._clock,
            step.options.get("timeout", DEFAULT_TIMEOUT_SECONDS),
        )
        spoken["name"] = spoken["name"] or reached["name"]
        self._people.learn(reached["key"], spoken["name"])
        if spoken["started"]:
            self._people.mark_talked(reached["key"])
        return {
            "key": reached["key"],
            "distance_m": reached["distance_m"],
            "talk_prompt": reached["talk_prompt"],
            **spoken,
        }

    def marker(self, step) -> dict:
        legs = []
        for _ in range(MARKER_LEGS):
            seen = self.hud()
            if seen["quest"] is None:
                return {
                    "arrived": False,
                    "reason": "hud hidden by a cutscene or dialogue: press nothing, poll hud",
                    "legs": legs,
                }
            if seen["marker_m"] is None or "marker_position" not in seen:
                return {
                    "arrived": False,
                    "reason": "no marker distance on the minimap",
                    "legs": legs,
                }
            if seen["marker_m"] <= MARKER_ARRIVAL_M:
                return {"arrived": True, "marker_m": seen["marker_m"], "legs": legs}
            player = self._steering.position()
            share = min(1.0, MARKER_LEG_M / seen["marker_m"])
            target_x = player.x + (seen["marker_position"][0] - player.x) * share
            target_z = player.z + (seen["marker_position"][1] - player.z) * share
            walked = self._walk(
                target_x,
                target_z,
                1.0,
                step.options.get("timeout", WALK_TIMEOUT_SECONDS),
            )
            legs.append(
                {
                    "marker_m": seen["marker_m"],
                    "bearing": seen["marker_bearing_degrees"],
                    "walk": walked["reason"],
                }
            )
            if not walked["arrived"] and walked["detours"]:
                return {
                    "arrived": False,
                    "reason": "blocked after detours",
                    "legs": legs,
                }
        return {"arrived": False, "reason": "marker not reached", "legs": legs}

    def prove_attack(self, step) -> dict:
        control = step.values[0] if step.values else "rb"
        return prove(
            self._devices.pad,
            control,
            self._devices.read_start_actions,
            self._pause,
            step.options.get("wait", DEFAULT_FLUSH_SECONDS),
        )

    def fight(self, step) -> dict:
        return hold_ground(
            self._devices.pad,
            self._bridge.read_state,
            self._walk,
            self._hazards,
            self._pause,
            self._clock,
            (step.values[0], step.values[1]),
            step.options.get("seconds", 20.0),
            step.options.get("leash", 8.0),
        )
