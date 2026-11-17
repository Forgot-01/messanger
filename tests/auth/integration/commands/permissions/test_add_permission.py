from dishka import AsyncContainer
import pytest

from app.auth.commands.permissions.add_permission_user import AddPermissionToUserCommand, AddPermissionToUserCommandHandler
from app.auth.exceptions import NotFoundPermissionsError
from app.core.utils import fromtimestamp


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestAddPermissionToUserCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> AddPermissionToUserCommandHandler:
        return await request_container.get(AddPermissionToUserCommandHandler)

    async def test_add_permission(
        self, handler, get_user_jwt_data, create_permissions, token_blacklist_repository
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data(role_name="system_admin")
        await create_permissions({"test:create", })

        await handler.handle(
            AddPermissionToUserCommand(
                permissions={"test:create", },
                user_id=user.id,
                user_jwt_data=user_jwt_data
            )
        )

        assert any(permission.name=="test:create" for permission in user.permissions)
        assert await token_blacklist_repository.get_user_blacklist(user.id) != fromtimestamp(float("0"))

    async def test_add_permissions(
        self, handler, get_user_jwt_data, create_permissions, token_blacklist_repository
    ) -> None:
        permissions = {"test:create", "test:update", "test:delete"}
        user, user_jwt_data = await get_user_jwt_data(role_name="system_admin")
        await create_permissions(permissions)

        await handler.handle(
            AddPermissionToUserCommand(
                permissions=permissions,
                user_id=user.id,
                user_jwt_data=user_jwt_data
            )
        )

        assert len([True for permission in user.permissions if permission.name in permissions]) == 3
        assert await token_blacklist_repository.get_user_blacklist(user.id) != fromtimestamp(float("0"))
        assert len(user.permissions) == 3

    async def test_not_found_permission(
        self, handler, get_user_jwt_data, create_permissions, token_blacklist_repository
    ) -> None:
        not_found_permissions = {"test:update", "test:delete"}
        user, user_jwt_data = await get_user_jwt_data(role_name="system_admin")
        await create_permissions({"test:create", })

        with pytest.raises(NotFoundPermissionsError) as error:
            await handler.handle(
                AddPermissionToUserCommand(
                    permissions=not_found_permissions,
                    user_id=user.id,
                    user_jwt_data=user_jwt_data
                )
            )
        assert error.value.missing == not_found_permissions

        assert await token_blacklist_repository.get_user_blacklist(user.id) == fromtimestamp(float("0"))

