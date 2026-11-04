from typing import TYPE_CHECKING, Self
from uuid import UUID, uuid7

from sqlalchemy import (
    UUID as SA_UUID,
    BigInteger,
    ForeignKey,
    Index,
    LargeBinary,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base_model import BaseModel

if TYPE_CHECKING:
    from app.auth.models.user import User


class Device(BaseModel):
    __tablename__ = "devices"

    id: Mapped[UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid7)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    did: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)

    os_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    fcm_token: Mapped[str] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="devices")

    __table_args__ = (
        Index("idx_devices_user_device", "user_id", "did", unique=True),
    )

    @classmethod
    def create(
        cls,
        user_id: int,
        did: str,
        device_name: str,
        platform: str,
        os_version: str | None,
        app_version: str | None,
        fcm_token: str,
    ) -> Self:
        return cls(
            id=uuid7(),
            user_id=user_id,
            did=did,
            device_name=device_name,
            platform=platform,
            os_version=os_version,
            app_version=app_version,
            fcm_token=fcm_token,
        )

    def update_fcm_token(self, fcm_token: str) -> None:
        self.fcm_token = fcm_token
