from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MYSQL_TABLE, Base, IdMixin, TimestampMixin, UnsignedInt

if TYPE_CHECKING:
    from app.models.user import User

# The address line at the foot of the request slip until the Admin changes it.
DEFAULT_ADDRESS_KH = (
    "ប្រអប់សំបុត្រលេខ ២៥, ផ្ទះលេខ ៨៨ ផ្លូវលេខ ១០២ កែងផ្លូវលេខ ១៩ សង្កាត់វត្តភ្នំ ខណ្ឌដូនពេញ "
    "រាជធានីភ្នំពេញ, ទូរស័ព្ទ ៖ (៨៥៥-២៣) ៧២២ ៥៦៣, ទូរស័ព្ទ / ទូរសារ ៖ (៨៥៥-២៣) ៩២៦ ១១៧"
)


class SlipSettings(IdMixin, TimestampMixin, Base):
    """The request slip's settings: one row, id 1. Who signs as Director of Cabinet, and the
    address printed at the foot."""

    __tablename__ = "slip_settings"
    __table_args__ = MYSQL_TABLE

    director_user_id: Mapped[int | None] = mapped_column(
        UnsignedInt, ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    address_kh: Mapped[str] = mapped_column(String(500), default=DEFAULT_ADDRESS_KH)

    director: Mapped["User | None"] = relationship()
