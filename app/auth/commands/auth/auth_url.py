import logging
import secrets
from dataclasses import dataclass

from app.auth.dtos.device import OAuthInfo, DeviceInfo
from app.auth.repositories.oauth import OAuthCodeRepository
from app.auth.services.oauth_manager import OAuthManager
from app.core.commands import BaseCommand, BaseCommandHandler


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreateOAuthAuthorizeUrlCommand(BaseCommand):
    provider: str
    user_id: int | None
    device_id: str
    platform: str
    device_name: str

    os_version: str | None
    app_version: str | None
    fcm_token: str | None
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class CreateOAuthAuthorizeUrlCommandHandler(BaseCommandHandler[CreateOAuthAuthorizeUrlCommand, str]):
    oauth_code_repository: OAuthCodeRepository
    oauth_manager: OAuthManager

    async def handle(self, command: CreateOAuthAuthorizeUrlCommand) -> str:
        state = self.oauth_manager.generate_state()
        code_verifier = self.oauth_manager.generate_code_verifier()
        code_challenge = self.oauth_manager.generate_code_challenge(verifier=code_verifier)

        await self.oauth_code_repository.add_oauth_info(
            state,
            OAuthInfo(
                user_id=command.user_id,
                device=DeviceInfo(
                    device_id=command.device_id,
                    device_name=command.device_name,
                    platform=command.platform,
                    os_version=command.os_version,
                    app_version=command.app_version,
                    fcm_token=command.fcm_token,
                ),
                ip_address=command.ip_address,
                user_agent=command.user_agent,
                code_verifier=code_verifier,
                provider=command.provider,
            )
        )

        logger.info("Login by oauth", extra={"provider": command.provider, "user_id": command.user_id})
        return await self.oauth_manager.get_authorize_url(
            provider_name=command.provider, state=state, code_challenge=code_challenge,
        )
