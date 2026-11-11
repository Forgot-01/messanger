
from uuid import UUID

import pytest
from dishka import AsyncContainer

from app.auth.commands.auth.logout import LogoutCommand, LogoutCommandHandler
from app.auth.exceptions import TokenInBlacklistError
from app.core.services.auth.dto import JwtTokenType
from app.core.services.auth.exceptions import InvalidTokenError


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestLogoutAuthCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> LogoutCommandHandler:
        return await request_container.get(LogoutCommandHandler)

    async def test_logout_success(
        self,
        handler,
        session_repository,
        auth_jwt_manager,
        get_user_and_token_group,
    ) -> None:
        user, token_group = await get_user_and_token_group()

        await handler.handle(
            LogoutCommand(
                refresh_token=token_group.refresh_token
            )
        )

        token = await auth_jwt_manager.validate_token(token_group.refresh_token, JwtTokenType.REFRESH)
        session = await session_repository.get_by_id(UUID(token.sid))
        assert session
        assert not session.is_active

        with pytest.raises(TokenInBlacklistError):
            await handler.handle(
                LogoutCommand(refresh_token=token_group.refresh_token)
            )

    async def test_logout_invalid_token(
        self,
        handler: LogoutCommandHandler,
    ) -> None:
        with pytest.raises(InvalidTokenError):
            await handler.handle(LogoutCommand(refresh_token="invalid_token"))

    async def test_logout_none_token(
        self,
        handler: LogoutCommandHandler,
    ) -> None:
        with pytest.raises(InvalidTokenError):
            await handler.handle(LogoutCommand(refresh_token=None))
