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
