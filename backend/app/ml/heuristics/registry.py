"""Central registry mapping heuristic ID (1-185) to implementation class."""
from __future__ import annotations
from typing import Type
from app.ml.heuristics.base import BaseHeuristic, Environment

_REGISTRY: dict[int, BaseHeuristic] = {}


def register(heuristic_instance: BaseHeuristic) -> None:
    hid = heuristic_instance.id
    if hid in _REGISTRY:
        raise ValueError(f"Duplicate heuristic ID {hid}: {_REGISTRY[hid].name} vs {heuristic_instance.name}")
    _REGISTRY[hid] = heuristic_instance


def get(hid: int) -> BaseHeuristic | None:
    return _REGISTRY.get(hid)


def get_all() -> dict[int, BaseHeuristic]:
    return dict(_REGISTRY)


def get_by_environment(env: Environment) -> dict[int, BaseHeuristic]:
    return {k: v for k, v in _REGISTRY.items() if v.environment == env}


def get_by_lens(lens: str) -> dict[int, BaseHeuristic]:
    return {k: v for k, v in _REGISTRY.items() if lens in v.lens_tags}


def get_registry_entries() -> list[dict]:
    """Return list of registry metadata for API consumption."""
    entries = []
    for hid, h in sorted(_REGISTRY.items()):
        entries.append({
            "id": h.id,
            "name": h.name,
            "environment": h.environment.value,
            "lens_tags": h.lens_tags,
            "description": h.description,
            "data_requirements": h.data_requirements,
        })
    return entries


def validate_completeness() -> list[str]:
    """Check all 185 IDs are registered with no gaps."""
    errors = []
    registered = set(_REGISTRY.keys())
    expected = set(range(1, 186))
    missing = expected - registered
    extra = registered - expected
    if missing:
        errors.append(f"Missing heuristic IDs: {sorted(missing)}")
    if extra:
        errors.append(f"Extra heuristic IDs outside 1-185: {sorted(extra)}")
    
    # Check environment ownership: no ID in two modules
    env_map: dict[int, str] = {}
    for hid, h in _REGISTRY.items():
        if hid in env_map and env_map[hid] != h.environment.value:
            errors.append(f"ID {hid} mapped to both {env_map[hid]} and {h.environment.value}")
        env_map[hid] = h.environment.value
    
    return errors
