from typing import TYPE_CHECKING, Self
from uuid import uuid7

from sqlalchemy import UUID, BigInteger, ForeignKey, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base_model import BaseModel

if TYPE_CHECKING:
    from app.auth.models.user import User


class Device(BaseModel):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(UUID, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    device_info: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(30))
    os_version: Mapped[str] = mapped_column(String(50))
    app_version: Mapped[str] = mapped_column(String(50))

    fcm_token: Mapped[str] = mapped_column(String(512), nullable=False)

    user_agent: Mapped[str] = mapped_column(String, nullable=False)
    ip_address: Mapped[str] = mapped_column(String, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_sessions_user_device", "user_id", "device_id"),
    )

    @classmethod
    def create(
        cls, user_id: int, did: str,
        ip_address: str,
        device_info: bytes,
        user_agent: str,
        device_name: str,
        platform: str,
        os_version: str,
        app_version: str,
        fcm_token: str,
    ) -> Self:
        instance = cls(
            id=uuid7(),
            user_id=user_id,
            device_id=did,
            device_info=device_info,
            device_name=device_name,
            platform=platform,
            os_version=os_version,
            app_version=app_version,
            fcm_token=fcm_token,
            user_agent=user_agent,
            ip_address=ip_address
        )
        return instance

    def update_fcm_token(self, fcm_token: str) -> None:
        self.fcm_token = fcm_token
