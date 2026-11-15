import pytest
from dishka import AsyncContainer

from app.auth.commands.users.change_username import ChangeUsernameCommand, ChangeUsernameCommandHandler
from app.auth.exceptions import InvalidUsernameError, UsernameTakenError


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestChangeUsernameCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> ChangeUsernameCommandHandler:
        return await request_container.get(ChangeUsernameCommandHandler)


    async def test_change_username(
        self,
        handler,
        get_user_jwt_data,
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data(username="base")
        user_dto = await handler.handle(
            ChangeUsernameCommand(
                user_jwt_data=user_jwt_data,
                username="new_username"
            )
        )

        assert user_dto.username == "new_username"
        assert user.username == "new_username"

    async def test_change_username_errors(
        self,
        handler,
        create_user,
        get_user_jwt_data,
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data(username="base")
        forgot_user = await create_user(username="forgot", email="forgot@gmail.com")

        with pytest.raises(UsernameTakenError) as error:
            await handler.handle(
                ChangeUsernameCommand(
                    username="forgot",
                    user_jwt_data=user_jwt_data
                )
            )
        assert error.value.username == "forgot"

        with pytest.raises(InvalidUsernameError) as error:
            await handler.handle(
                ChangeUsernameCommand(
                    username="forgot=1!",
                    user_jwt_data=user_jwt_data
                )
            )
        assert error.value.reason == "format"

        with pytest.raises(InvalidUsernameError) as error:
            await handler.handle(
                ChangeUsernameCommand(
                    username="1234",
                    user_jwt_data=user_jwt_data
                )
            )

        assert error.value.reason == "length"

        with pytest.raises(InvalidUsernameError) as error:
            await handler.handle(
                ChangeUsernameCommand(
                    username="1"*33,
                    user_jwt_data=user_jwt_data
                )
            )

        assert error.value.reason == "length"

        with pytest.raises(InvalidUsernameError) as error:
            await handler.handle(
                ChangeUsernameCommand(
                    username="admin",
                    user_jwt_data=user_jwt_data
                )
            )

        assert error.value.reason == "reserved"
