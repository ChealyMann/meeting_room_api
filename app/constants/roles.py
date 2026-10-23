from enum import StrEnum


class RoleCode(StrEnum):
    """The six fixed role codes, in seed order (spec section 5).

    Code always checks these codes, never the display names. The order is also the order
    `roles` and `role_codes` are returned in.
    """

    ADMIN = "ADMIN"
    ROOM_OWNER = "ROOM_OWNER"
    STAFF = "STAFF"
    PITIKA = "PITIKA"
    IT_LEAD = "IT_LEAD"
    IT_STAFF = "IT_STAFF"


_SEED_ORDER = {code.value: index for index, code in enumerate(RoleCode)}


def seed_order(code: str) -> int:
    """Sort key for roles and role codes: seed order, unknown codes last."""
    return _SEED_ORDER.get(code, len(_SEED_ORDER))
