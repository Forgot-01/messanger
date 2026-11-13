import pytest
from dishka import AsyncContainer

from app.auth.commands.users.change_password import ChangePasswordCommand, ChangePasswordCommandHandler
from app.auth.exceptions import PasswordMismatchError
from app.core.utils import fromtimestamp


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestChangePasswordCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> ChangePasswordCommandHandler:
        return await request_container.get(ChangePasswordCommandHandler)


    async def test_change_password_success(
        self, handler, get_user_jwt_data, hash_service,
        token_blacklist_repository,
    ) -> None:
        old_password = "BasePass123!"
        new_password = "NewPass123!"

        user, user_jwt_data = await get_user_jwt_data(
            password=old_password,
        )

        await handler.handle(
            ChangePasswordCommand(
                old_password=old_password,
                new_password=new_password,
                new_password_repeat=new_password,
                user_jwt_data=user_jwt_data
            )
        )

        assert hash_service.verify_password(new_password, user.password_hash)
        assert await token_blacklist_repository.get_user_blacklist(user.id) != fromtimestamp(float("0"))


    async def test_change_password_errors(
        self, handler, get_user_jwt_data, token_blacklist_repository
    ) -> None:
        old_password = "BasePass123!"
        new_password = "NewPass123!"
        user, user_jwt_data = await get_user_jwt_data(
            password=old_password,
        )

        with pytest.raises(PasswordMismatchError):
            await handler.handle(
                ChangePasswordCommand(
                    old_password="WrongPass123!",
                    new_password=new_password,
                    new_password_repeat=new_password,
                    user_jwt_data=user_jwt_data
                )
            )

        with pytest.raises(PasswordMismatchError):
            await handler.handle(
                ChangePasswordCommand(
                    old_password=old_password,
                    new_password=new_password,
                    new_password_repeat="WrongRepeatNewPass123!",
                    user_jwt_data=user_jwt_data
                )
            )

        assert await token_blacklist_repository.get_user_blacklist(user.id) == fromtimestamp(float("0"))
