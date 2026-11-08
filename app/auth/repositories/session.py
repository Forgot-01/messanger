from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select

from app.auth.config import auth_config
from app.auth.models.session import Session
from app.core.db.repository import IRepository
from app.core.utils import fromtimestamp, now_utc


@dataclass
class SessionRepository(IRepository[Session]):
    async def get_by_id(self, session_id: UUID) -> Session | None:
        query = select(Session).where(Session.id == session_id)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_active_by_device(self, user_id: int, device_id: UUID) -> Session | None:
        query = select(Session).where(
            Session.user_id == user_id,
            Session.device_id == device_id,
            Session.revoked_at.is_(None)
        )
        result = await self.session.execute(query)
        return result.scalar()

    async def get_active_by_user(self, user_id: int) -> list[Session]:
        query = select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
        result = await self.session.execute(query)
        return list(result.scalars())

    async def create(self, session: Session) -> None:
        self.session.add(session)


@dataclass
class TokenBlacklistRepository:
    client: Redis

    async def add_jwt_token(self, jti: str, expiration: timedelta | None=None) -> None:
        await self.client.set(
            f"revoked:{jti}",  str(now_utc().timestamp()), ex=expiration
        )

    async def is_token_revoked(self, jti: str) -> bool:
        return bool(await self.client.exists(f"revoked:{jti}"))

    async def add_user(self, user_id: int, expiration: timedelta | None=None) -> None:
        if expiration is None:
            expiration = timedelta(minutes=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES + 1)

        await self.client.set(
            f"user:{user_id}",  str(now_utc().timestamp()), ex=expiration
        )

    async def get_user_blacklist(self, user_id: int)  -> datetime:
        time_str = await self.client.get(f"user:{user_id}") or "0"
        return fromtimestamp(float(time_str))

    async def add_token(self, token: str, user_id: int, expiration: timedelta) -> None:
        await self.client.set(
            token,
            value=user_id,
            ex=expiration
        )

    async def is_valid_token(self, token: str) -> int | None:
        user_id = await self.client.get(token)
        return int(user_id) if user_id is not None else None

    async def invalidate_token(self, token: str) -> None:
        await self.client.delete(token)
