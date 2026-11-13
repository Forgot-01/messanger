from uuid import UUID

import pytest
from dishka import AsyncContainer

from app.auth.commands.sessions.deactivate_session import (
    UserDeactivateSessionCommand,
    UserDeactivateSessionCommandHandler,
)
from app.auth.dtos.user import AuthUserJWTData
from app.auth.exceptions import NotFoundOrInactiveSessionError


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestDeactivateCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> UserDeactivateSessionCommandHandler:
        return await request_container.get(UserDeactivateSessionCommandHandler)

    @pytest.fixture
    async def get_data(
        self, get_user_and_token_group, auth_jwt_manager, session_repository
    ):
        user, token_group = await get_user_and_token_group()
        token = await auth_jwt_manager.validate_token(token_group.access_token)
        user_jwt_data = AuthUserJWTData.create_from_token(token)

        session = await session_repository.get_by_id(UUID(token.sid), with_device=True)

        return session, user_jwt_data

    async def test_deactivate_session_success(
        self, handler, get_data
    ) -> None:
        session, user_jwt_data = get_data

        await handler.handle(
            UserDeactivateSessionCommand(
                session_id=session.id,
                user_jwt_data=user_jwt_data,
            )
        )

        assert session.is_active is False


    async def test_deactivate_session_not_permmission(
        self, handler, get_data,
    ) -> None:
        session, user_jwt_data = get_data

        user_jwt_data.id = 999_999
        with pytest.raises(NotFoundOrInactiveSessionError):
            await handler.handle(
                UserDeactivateSessionCommand(
                    session_id=session.id,
                    user_jwt_data=user_jwt_data,
                )
            )

    async def test_deactivate_session_admin(
        self, handler, get_data,
    ) -> None:
        session, user_jwt_data = get_data

        user_jwt_data.id = 999_999
        user_jwt_data.permissions.append("user:update")

        await handler.handle(
            UserDeactivateSessionCommand(
                session_id=session.id,
                user_jwt_data=user_jwt_data,
            )
        )

        assert session.is_active is False

