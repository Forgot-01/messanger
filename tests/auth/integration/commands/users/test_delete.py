import pytest
from dishka import AsyncContainer

from app.auth.commands.users.delete import DeleteUserCommand, DeleteUserCommandHandler
from app.core.services.auth.exceptions import AccessDeniedError
from app.core.utils import fromtimestamp


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestDeleteCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> DeleteUserCommandHandler:
        return await request_container.get(DeleteUserCommandHandler)

    async def test_delete_own_user_success(
        self, handler, get_user_jwt_data, token_blacklist_repository
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data()
        await handler.handle(
            DeleteUserCommand(
                user_id=user.id,
                user_jwt_data=user_jwt_data,
            )
        )

        assert user.deleted_at is not None
        assert await token_blacklist_repository.get_user_blacklist(user.id) != fromtimestamp(float("0"))

    async def test_delete_sys_user_success(
        self, handler, create_user, get_user_jwt_data, token_blacklist_repository
    ) -> None:
        standart_user = await create_user(username="standart_user", email="standart_user@gmail.com")
        user, user_jwt_data = await get_user_jwt_data(role_name="system_admin")

        await handler.handle(
            DeleteUserCommand(
                user_id=standart_user.id,
                user_jwt_data=user_jwt_data,
            )
        )

        assert standart_user.deleted_at is not None
        assert await token_blacklist_repository.get_user_blacklist(standart_user.id) != fromtimestamp(float("0"))
        assert user.deleted_at is None

    async def test_delete_user_without_permission(
        self, handler, create_user, get_user_jwt_data, token_blacklist_repository
    ) -> None:
        standart_user = await create_user(username="standart_user", email="standart_user@gmail.com")
        other_user, user_jwt_data = await get_user_jwt_data()

        with pytest.raises(AccessDeniedError):
            await handler.handle(
                DeleteUserCommand(
                    user_id=standart_user.id,
                    user_jwt_data=user_jwt_data,
                )
            )

        assert standart_user.deleted_at is None
        assert await token_blacklist_repository.get_user_blacklist(standart_user.id) == fromtimestamp(float("0"))
        assert other_user.deleted_at is None
