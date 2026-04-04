"""Validation contract: exactly 185 unique IDs, no overlap, no missing."""
from app.ml.heuristics.registry import validate_completeness


def check() -> bool:
    """Return True if all 185 heuristics are registered correctly."""
    errors = validate_completeness()
    if errors:
        for e in errors:
            print(f"COMPLETENESS ERROR: {e}")
        return False
    print("All 185 heuristics registered correctly.")
    return True


if __name__ == "__main__":
    check()
