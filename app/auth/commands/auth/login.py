import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dtos.tokens import TokenGroup
from app.auth.dtos.user import AuthUserJWTData
from app.auth.exceptions import WrongLoginDataError
from app.auth.repositories.user import UserRepository
from app.auth.services.hash import HashService
from app.auth.services.jwt import AuthJWTManager
from app.auth.services.session import DeviceSessionManager
from app.core.commands import BaseCommand, BaseCommandHandler
from app.core.events.service import BaseEventBus

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class LoginCommand(BaseCommand):
    username: str
    password: str

    device_id: str
    platform: str
    device_name: str

    os_version: str | None
    app_version: str | None
    fcm_token: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class LoginCommandHandler(BaseCommandHandler[LoginCommand, TokenGroup]):
    session: AsyncSession
    user_repository: UserRepository
    session_manager: DeviceSessionManager
    jwt_manager: AuthJWTManager
    hash_service: HashService
    event_bus: BaseEventBus

    async def handle(self, command: LoginCommand) -> TokenGroup:
        if "@" in command.username:
            user = await self.user_repository.get_with_roles_by_email(command.username)
        else:
            user = await self.user_repository.get_with_roles_by_username(command.username)

        if (
            (user is None) or
            (user.is_deleted) or
            (user.password_hash is None) or
            (not self.hash_service.verify_password(command.password, user.password_hash))
        ):
            raise WrongLoginDataError(username=command.username)

        device, session = await self.session_manager.get_or_create_session(
            user_id=user.id, did=command.device_id, device_name=command.device_name,
            platform=command.platform, os_version=command.os_version,
            app_version=command.app_version, fcm_token=command.fcm_token,
            ip_address=command.ip_address, user_agent=command.ip_address
        )

        await self.event_bus.publish(session.pull_events())
        await self.session.commit()

        token_group = self.jwt_manager.create_token_pair(
            AuthUserJWTData.create_from_user(user, device_id=str(device.id), session_id=str(session.id))
        )

        logger.info("Logining user", extra={"user_id": user.id, "device_id": session.device_id})
        return token_group
