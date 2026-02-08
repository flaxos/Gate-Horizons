"""Helpers for building planet comparison data."""


def build_comparison_data(system, body_ids: list[str]) -> list[dict]:
    data = []
    if not system:
        return data
    surveyed = bool(getattr(system, "surveyed", False))
    for body_id in body_ids:
        if not surveyed:
            data.append(
                {
                    "id": body_id,
                    "name": "Unknown Body",
                    "type": "unknown",
                    "habitability": 0.0,
                    "gravity": 0.0,
                    "traits": [],
                    "resources": {},
                    "colonizable": False,
                    "surveyed": False,
                }
            )
            continue
        planet = next((p for p in system.planets if p.id == body_id), None)
        if not planet:
            continue
        data.append(
            {
                "id": planet.id,
                "name": planet.name,
                "type": planet.type,
                "habitability": planet.habitability,
                "gravity": planet.gravity,
                "traits": list(planet.traits or []),
                "resources": dict(planet.resources or {}),
                "colonizable": planet.colonizable,
                "surveyed": True,
            }
        )
    return data
