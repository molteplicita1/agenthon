"""CONTRACT section 5 rules 1, 2, 3 and 6. Pure functions, no state."""


def can_see(user: dict, item: dict) -> bool:
    """Rule 1: visible_to contains "all" or the user's team. Works for sources and memory items."""
    return "all" in item["visible_to"] or user["team"] in item["visible_to"]


def is_lead_of(user: dict, team: str) -> bool:
    return user["is_lead"] and user["team"] == team


def can_see_memory(user: dict, m: dict) -> bool:
    """Rules 1 and 2: approved items by visibility; proposed and rejected only for the team lead."""
    if m["status"] == "approved":
        return can_see(user, m)
    return is_lead_of(user, m["team"])


def can_decide_memory(user: dict, m: dict) -> bool:
    """Rule 3, plus: only proposed items can still be decided."""
    return m["status"] == "proposed" and is_lead_of(user, m["team"])


def visible_approved_memory(user: dict, items: list) -> list:
    return [m for m in items if m["status"] == "approved" and can_see(user, m)]
