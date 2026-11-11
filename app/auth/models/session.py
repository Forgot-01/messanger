from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID, uuid7

from sqlalchemy import (
    UUID as SA_UUID,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models.device import Device
from app.core.db.base_model import BaseModel
from app.core.events.event import BaseEvent
from app.core.utils import now_utc

if TYPE_CHECKING:
    from app.auth.models.user import User


@dataclass(frozen=True)
class NewSessionEvent(BaseEvent):
    user_id: int
    device_id: str

    __event_name__: str = "auth.session.created"

    def get_aggregate_id(self) -> str:
        return str(self.user_id)


@dataclass(frozen=True)
class DeactivateSessionEvent(BaseEvent):
    user_id: int
    device_id: str

    __event_name__: str = "auth.session.deactivated"

    def get_aggregate_id(self) -> str:
        return str(self.user_id)


@dataclass(frozen=True)
class SuspiciousSessionEvent(BaseEvent):
    user_id: int
    session_id: int
    reason: str
    old_value: str | None
    new_value: str | None

    __event_name__: str = "auth.session.suspicious"

    def get_aggregate_id(self) -> str:
        return str(self.user_id)


class Session(BaseModel):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        index=True, nullable=False
    )

    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    user_agent: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="sessions")
    device: Mapped[Device] = relationship("Device")

    __table_args__ = (
        Index("idx_sessions_user_device", "user_id", "device_id"),
    )


    @classmethod
    def create(
        cls,
        user_id: int,
        device_id: UUID,
        ip_address: str,
        user_agent: str,
    ) -> Self:
        instance = cls(
            id=uuid7(),
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            last_ip_address=ip_address,
            revoked_at=None,
        )

        instance.register_event(
            NewSessionEvent(
                user_id=user_id,
                device_id=str(device_id)
            )
        )
        return instance

    def deactivate(self) -> None:
        now = now_utc()
        self.revoked_at = now
        self.last_activity = now
        self.register_event(
            DeactivateSessionEvent(
                user_id=self.user_id,
                device_id=str(self.device_id)
            )
        )

    def online(self, ip_adress: str) -> None:
        self.last_activity = now_utc()
        self.last_ip_address = ip_adress

    @property
    def is_active(self) -> bool:
        return self.revoked_at >= now_utc() if self.revoked_at else True

