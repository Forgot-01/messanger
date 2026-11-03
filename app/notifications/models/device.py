
from sqlalchemy import (
    BigInteger,
    Boolean,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base_model import BaseModel, DateMixin


class UserDeviceToken(BaseModel, DateMixin):
    __tablename__ = "user_device_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    did: Mapped[int] = mapped_column(String(128), nullable=False)
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("user_id", "token", name="uq_device_token"),
        UniqueConstraint("user_id", "did", name="uq_device_did"),
        Index("ix_device_tokens_user_active", "user_id", "is_active"),
    )

    @classmethod
    def create(
        cls, user_id: int, token: str, platform: str,
        device_name: str, did: str
    ) -> UserDeviceToken:
        instance = cls(
            user_id=user_id,
            token=token,
            platform=platform,
            device_name=device_name,
            did=did
        )
        return instance

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False
