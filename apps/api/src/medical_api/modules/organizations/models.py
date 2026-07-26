from sqlalchemy.orm import Mapped, mapped_column

from medical_api.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(index=True)
    legal_name: Mapped[str | None]
    timezone: Mapped[str] = mapped_column(default="America/Bogota")
    is_active: Mapped[bool] = mapped_column(default=True)
