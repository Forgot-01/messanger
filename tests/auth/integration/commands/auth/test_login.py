from uuid import UUID, uuid4

import pytest
from dishka import AsyncContainer

from app.auth.commands.auth.login import LoginCommandHandler
from app.auth.exceptions import WrongLoginDataError
from tests.auth.integration.utils import create_login_command


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestLoginAuthCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer,
    ) -> LoginCommandHandler:
        return await request_container.get(LoginCommandHandler)

    async def test_login_success(
        self,
        handler,
        create_user,
        session_repository,
        device_repository,
        auth_jwt_manager,
    ) -> None:
        device_id = str(uuid4())
        user = await create_user(
                email="base@gmail.com",
                username="forgot",
                password="Test12345!"
        )

        token_group1 = await handler.handle(
            create_login_command(
                username="forgot",
                password="Test12345!",
                device_id=device_id
            )
        )

        assert token_group1

        token1 = await auth_jwt_manager.validate_token(token_group1.access_token)
        session1 = await session_repository.get_by_id(UUID(token1.sid), with_device=True)

        assert session1 is not None
        assert session1.is_active
        assert session1.user_id == user.id
        assert session1.device.user_id == user.id

        token_group2 = await handler.handle(
            create_login_command(
                username="base@gmail.com",
                password="Test12345!",
                device_id=device_id
            )
        )

        assert token_group2
        token2 = await auth_jwt_manager.validate_token(token_group2.access_token)
        session2 = await session_repository.get_by_id(UUID(token2.sid), with_device=True)

        assert session2 is not None
        assert session2.is_active
        assert session2.user_id == user.id
        assert session2.device.user_id == user.id

        assert session1.device_id == session2.device_id
        assert session1.id != session2.id
        assert not session1.is_active

        token_group3 = await handler.handle(
            create_login_command(
                username="base@gmail.com",
                password="Test12345!",
            )
        )

        assert token_group3
        token3 = await auth_jwt_manager.validate_token(token_group3.access_token)
        session3 = await session_repository.get_by_id(UUID(token3.sid), with_device=True)

        assert session3 is not None
        assert session3.is_active
        assert session3.user_id == user.id
        assert session3.device.user_id == user.id

        assert session2.device_id != session3.device_id
        assert session2.id != session3.id
        assert session2.is_active

        devices = await device_repository.get_user_devices(user.id)
        assert len(devices) == 2

    @pytest.mark.parametrize(
        ("username", "password"),
        [
            pytest.param("forgot", "WrongPassword123!", id="wrong-password"),
            pytest.param("unknown", "Test12345!", id="unknown-username"),
            pytest.param("unknown@gmail.com", "Test12345!", id="unknown-email"),
            pytest.param("", "Test12345!", id="empty-username"),
            pytest.param("forgot", "", id="empty-password"),
        ],
    )
    async def test_login_with_invalid_credentials(
        self,
        handler,
        create_user,
        username: str,
        password: str,
    ) -> None:
        await create_user(
            email="base@gmail.com",
            username="forgot",
            password="Test12345!",
        )

        with pytest.raises(WrongLoginDataError):
            await handler.handle(
                create_login_command(
                    username=username,
                    password=password,
                )
            )
