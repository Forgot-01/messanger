from dishka import AsyncContainer
import pytest

from app.auth.commands.permissions.remove_permission_user import (
    DeletePermissionToUserCommand,
    DeletePermissionToUserCommandHandler
)
from app.auth.exceptions import NotFoundPermissionsError
from app.core.utils import fromtimestamp


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestRemovePermissionToUserCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> DeletePermissionToUserCommandHandler:
        return await request_container.get(DeletePermissionToUserCommandHandler)


    async def test_remove_success(
        self, handler, get_user_jwt_data, create_permissions, token_blacklist_repository
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data(role_name="system_admin")
        await create_permissions({"test:create", }, user)

        await handler.handle(
            DeletePermissionToUserCommand(
                user_id=user.id,
                permissions={"test:create", },
                user_jwt_data=user_jwt_data,
            )
        )

        assert all(
            permission.name != "test:create" for permission in user.permissions
        )
        assert await token_blacklist_repository.get_user_blacklist(user.id) != fromtimestamp(float("0"))


    
    async def test_remove_permissions(
        self, handler, get_user_jwt_data, create_permissions, token_blacklist_repository
    ) -> None:
        permissions = {"test:create", "test:update", "test:delete"}
        user, user_jwt_data = await get_user_jwt_data(role_name="system_admin")
        await create_permissions(permissions, user)

        await handler.handle(
            DeletePermissionToUserCommand(
                permissions=permissions,
                user_id=user.id,
                user_jwt_data=user_jwt_data
            )
        )

        assert len([True for permission in user.permissions if permission.name in permissions]) == 0
        assert await token_blacklist_repository.get_user_blacklist(user.id) != fromtimestamp(float("0"))
        assert len(user.permissions) == 0

    async def test_not_found_permission(
        self, handler, get_user_jwt_data, create_permissions, token_blacklist_repository
    ) -> None:
        not_found_permissions = {"test:update", "test:delete"}
        user, user_jwt_data = await get_user_jwt_data(role_name="system_admin")
        await create_permissions({"test:create", }, user)

        with pytest.raises(NotFoundPermissionsError) as error:
            await handler.handle(
                DeletePermissionToUserCommand(
                    permissions=not_found_permissions,
                    user_id=user.id,
                    user_jwt_data=user_jwt_data
                )
            )
        assert error.value.missing == not_found_permissions

        assert await token_blacklist_repository.get_user_blacklist(user.id) == fromtimestamp(float("0"))


