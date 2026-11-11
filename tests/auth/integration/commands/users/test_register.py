from dishka import AsyncContainer
import pytest

from app.auth.commands.users.register import RegisterCommand, RegisterCommandHandler
from app.auth.dtos.user import UserDTO
from app.auth.exceptions import DuplicateUserError, InvalidUsernameError, PasswordMismatchError
from app.auth.models.role_permission import RolesEnum


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestRegisterCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> RegisterCommandHandler:
        return await request_container.get(RegisterCommandHandler)

    async def test_register_success(
        self,
        handler,
    ) -> None:
        user: UserDTO = await handler.handle(
            RegisterCommand(
                username="forgot",
                email="base@gmail.com",
                password="TestPass1234!",
                password_repeat="TestPass1234!"
            )
        )

        assert user.username == "forgot"
        assert user.email == "base@gmail.com"
        assert len(user.roles) == 1
        assert user.roles[0].name == RolesEnum.STANDARD_USER.value.name
        assert user.is_active
        assert user.is_verified is False

    async def test_errors(
        self, handler, get_user_and_token_group,
    ) -> None:
        user, token_group = await get_user_and_token_group(
            username="forgot",
            email="base@gmail.com",
        )

        with pytest.raises(DuplicateUserError):
            await handler.handle(
                RegisterCommand(
                    username="forgot",
                    email="unique@gmail.com",
                    password="TestPass1234!",
                    password_repeat="TestPass1234!"
                )
            )

        with pytest.raises(InvalidUsernameError):
            await handler.handle(
                RegisterCommand(
                    username="system",
                    email="unique@gmail.com",
                    password="TestPass1234!",
                    password_repeat="TestPass1234!"
                )
            )

        with pytest.raises(DuplicateUserError):
            await handler.handle(
                RegisterCommand(
                    username="unique",
                    email="base@gmail.com",
                    password="TestPass1234!",
                    password_repeat="TestPass1234!"
                )
            )

        with pytest.raises(PasswordMismatchError):
            await handler.handle(
                RegisterCommand(
                    username="unique",
                    email="unique@gmail.com",
                    password="TestPass1234!",
                    password_repeat="MissMatchTestPass1234!"
                )
            )
