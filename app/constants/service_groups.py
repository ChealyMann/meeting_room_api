from enum import StrEnum


class FoodGroup(StrEnum):
    """The group a catering package shows under on the Staff booking page (owner decision,
    12 Nov 2026). None means "Other", shown last."""

    BREAKFAST = "BREAKFAST"
    MEALS = "MEALS"
    BREAKS = "BREAKS"


class ITGroup(StrEnum):
    """The group an IT service shows under on the Staff booking page. None means "Other"."""

    SCREENS = "SCREENS"
    SOUND = "SOUND"
    DEVICES = "DEVICES"
    SUPPORT = "SUPPORT"
