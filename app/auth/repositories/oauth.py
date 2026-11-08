from dataclasses import dataclass
from datetime import timedelta

from redis.asyncio import Redis
from sqlalchemy import select

from app.auth.dtos.device import OAuthInfo
from app.auth.models.oauth import OAuthAccount, OAuthProviderEnum
from app.core.db.repository import IRepository


@dataclass
class OauthAccountRepository(IRepository[OAuthAccount]):
    async def create(self, oauth_account: OAuthAccount) -> None:
        self.session.add(oauth_account)

    async def get_by_id(self, account_id: int) -> OAuthAccount | None:
        query = select(OAuthAccount).where(OAuthAccount.id == account_id)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_by_provider_and_user_id(
        self, provider: OAuthProviderEnum, provider_user_id: str
    ) -> OAuthAccount | None:
        query = select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id
        )
        result = await self.session.execute(query)
        return result.scalar()

    async def get_by_user_id(self, user_id: int) -> list[OAuthAccount]:
        query = select(OAuthAccount).where(OAuthAccount.user_id == user_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())


@dataclass
class OAuthCodeRepository:
    client: Redis

    async def add_oauth_info(self, state: str, auth_info: OAuthInfo) -> None:
            await self.client.set(
                f"oauth:state:{state}", auth_info.model_dump_json(), ex=timedelta(minutes=10)
            )

    async def getdel_oauth_info(self, state: str) -> OAuthInfo | None:
        auth_info = await self.client.getdel(f"oauth:state:{state}")
        if auth_info is None:
            return None

        return OAuthInfo.model_validate_json(auth_info)
