from uuid import UUID

import jwt
import pytest
from dishka import AsyncContainer

from app.auth.commands.auth.login import LoginCommandHandler
from app.auth.commands.auth.refresh_token import RefreshTokenCommand, RefreshTokenCommandHandler
from app.auth.exceptions import NotFoundOrInactiveSessionError, TokenInBlacklistError
from app.core.services.auth.exceptions import InvalidTokenError
from tests.auth.integration.utils import create_login_command


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestRefreshTokenAuthCommand:
    @pytest.fixture
    async def login_handler(
        self,
        request_container: AsyncContainer,
    ) -> LoginCommandHandler:
        return await request_container.get(LoginCommandHandler)

    @pytest.fixture
    async def refresh_handler(
        self,
        request_container: AsyncContainer,
    ) -> RefreshTokenCommandHandler:
        return await request_container.get(RefreshTokenCommandHandler)

    @pytest.fixture
    def get_user_and_token_group(
        self,
        create_user,
        login_handler,
    ):
        async def create(
            email: str = "base@gmail.com",
            username: str = "standartser",
            password: str = "TestPass123!",
            is_verified: bool = False,
            role_name: str = "user",
            permission_names: set[str] | None=None,
        ):
            user = await create_user(
                email=email,
                username=username,
                password=password,
                is_verified=is_verified,
                role_name=role_name,
                permission_names=permission_names
            )
            token_group = await login_handler.handle(
                create_login_command(
                    username=username,
                    password=password,
                )
            )
            return user, token_group
        return create

    async def test_refresh_token_success(
        self,
        refresh_handler,
        session_repository,
        auth_jwt_manager,
        get_user_and_token_group
    ) -> None:
        user, token_group = await get_user_and_token_group()

        assert token_group
        old_token = await auth_jwt_manager.validate_token(token_group.access_token)
        old_session = await session_repository.get_by_id(UUID(old_token.sid), with_device=True)

        assert old_session.is_active
        assert str(old_session.ip_address) == "127.0.0.1"
        assert old_session.last_ip_address == old_session.ip_address

        refresh_token_group = await refresh_handler.handle(
            RefreshTokenCommand(refresh_token=token_group.refresh_token, ip_address="127.0.1.1")
        )

        token = await auth_jwt_manager.validate_token(refresh_token_group.access_token)
        session = await session_repository.get_by_id(UUID(token.sid), with_device=True)

        assert session.is_active
        assert str(session.last_ip_address) == "127.0.1.1"
        assert session.last_activity >= old_session.last_activity

    async def test_rotation_refresh(
        self,
        refresh_handler,
        session_repository,
        auth_jwt_manager,
        get_user_and_token_group,
    ) -> None:
        user, token_group = await get_user_and_token_group()

        refresh_token_group = await refresh_handler.handle(
            RefreshTokenCommand(refresh_token=token_group.refresh_token, ip_address="127.0.1.1")
        )

        with pytest.raises(TokenInBlacklistError):
            await refresh_handler.handle(
                RefreshTokenCommand(refresh_token=token_group.refresh_token, ip_address="127.0.1.1")
            )

        assert refresh_token_group
        token = await auth_jwt_manager.validate_token(refresh_token_group.access_token)
        session = await session_repository.get_by_id(UUID(token.sid), with_device=True)

        assert not session.is_active
        with pytest.raises(NotFoundOrInactiveSessionError):
            await refresh_handler.handle(
                RefreshTokenCommand(refresh_token=token_group.refresh_token, ip_address="127.0.1.1")
            )

    async def test_user_blacklist(
        self,
        refresh_handler,
        token_blacklist_repository,
        get_user_and_token_group,
    ) -> None:
        user, token_group = await get_user_and_token_group()

        await token_blacklist_repository.add_user(user.id)
        with pytest.raises(TokenInBlacklistError):
            await refresh_handler.handle(
                RefreshTokenCommand(refresh_token=token_group.refresh_token, ip_address="127.0.1.1")
            )

    async def test_role_blacklist(
        self,
        refresh_handler,
        role_blacklist,
        get_user_and_token_group,
    ) -> None:
        user, token_group = await get_user_and_token_group(role_name="user")

        await role_blacklist.invalidate_role("user")
        with pytest.raises(TokenInBlacklistError):
            await refresh_handler.handle(
                RefreshTokenCommand(refresh_token=token_group.refresh_token, ip_address="127.0.1.1")
            )

    async def test_permission_blacklist(
        self,
        refresh_handler,
        permission_blacklist,
        get_user_and_token_group
    ) -> None:
        user, token_group = await get_user_and_token_group(permission_names={"user:update", })

        await permission_blacklist.invalidate_permission("user:update")
        with pytest.raises(TokenInBlacklistError):
            await refresh_handler.handle(
                RefreshTokenCommand(refresh_token=token_group.refresh_token, ip_address="127.0.1.1")
            )

    async def test_invalid_token(
        self,
        refresh_handler,
    ) -> None:
        refresh_invalid_token = jwt.encode(
            {
                "sub": "1",
                "roles": ["admin"]
            }, "invalid_secret_key_for_testing_32", algorithm="HS256"
        )
        with pytest.raises(InvalidTokenError):
            await refresh_handler.handle(
                RefreshTokenCommand(refresh_token=refresh_invalid_token, ip_address="127.0.0.1")
            )
