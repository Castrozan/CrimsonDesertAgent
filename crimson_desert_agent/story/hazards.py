import math

from ..scripting.steering import NotInWorld

HAZARD_RADIUS_M = 3.0
ENEMY_REACH_M = 3.0
HEALTH_DROP = 3.0
SAFE_TRAIL_SECONDS = 2.0


class Burning(NotInWorld):
    pass


class Hazards:
    def __init__(self) -> None:
        self.places: list[tuple[float, float]] = []
        self.last_safe: tuple[float, float] | None = None
        self._health: float | None = None
        self.retreating = False
        self._trail: list[tuple[float, float, float]] = []

    def near(self, x: float, z: float, radius: float = HAZARD_RADIUS_M) -> bool:
        return any(
            math.hypot(x - place_x, z - place_z) <= radius
            for place_x, place_z in self.places
        )

    def crossed_by(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> tuple[float, float] | None:
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        for place in self.places:
            if length == 0:
                continue
            along = (
                (place[0] - start[0]) * (end[0] - start[0])
                + (place[1] - start[1]) * (end[1] - start[1])
            ) / length
            if not 0.0 <= along <= length:
                continue
            closest = (
                start[0] + (end[0] - start[0]) * along / length,
                start[1] + (end[1] - start[1]) * along / length,
            )
            if (
                math.hypot(place[0] - closest[0], place[1] - closest[1])
                <= HAZARD_RADIUS_M
            ):
                return place
        return None

    def watching(self, read_state, clock):
        def read() -> dict:
            state = read_state()
            player = state.get("player")
            if not player or player.get("health") is None:
                return state
            x, z, health, now = (
                player["position"][0],
                player["position"][2],
                player["health"],
                clock(),
            )
            enemy_near = any(
                actor.get("kind") == "character"
                and actor.get("distance", 99.0) <= ENEMY_REACH_M
                for actor in state.get("actors") or []
            )
            burning = (
                self._health is not None
                and self._health - health >= HEALTH_DROP
                and not enemy_near
                and health > 0
            )
            self._health = health
            if burning and not self.retreating:
                if not self.near(x, z, 1.5):
                    self.places.append((round(x, 1), round(z, 1)))
                raise Burning(
                    "burning: health is falling with no enemy near; the place is recorded as a hazard"
                )
            self._trail = [
                entry for entry in self._trail if now - entry[0] <= SAFE_TRAIL_SECONDS
            ] + [(now, x, z)]
            if not self.near(x, z):
                self.last_safe = (self._trail[0][1], self._trail[0][2])
            return state

        return read
