import pytest
from dishka import AsyncContainer

from app.auth.commands.permissions.delete import DeletePermissionCommand, DeletePermissionCommandHandler
from app.auth.exceptions import ProtectedPermissionError


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestCreateCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> DeletePermissionCommandHandler:
        return await request_container.get(DeletePermissionCommandHandler)

    async def test_delete_sccess(
        self, handler, get_user_jwt_data,
        permission_repository, create_permissions, permission_blacklist
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data(role_name="super_admin")
        await create_permissions({"new:permission", })

        await handler.handle(
            DeletePermissionCommand(
                name="new:permission",
                user_jwt_data=user_jwt_data
            )
        )

        permission = await permission_repository.get_permission_by_name("new:permission")
        assert permission is None
        assert permission_blacklist.get_permission_invalidation_time("new:permission") is not None

    async def test_delete_protected(
        self, handler, get_user_jwt_data, permission_blacklist,
        permission_repository
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data(role_name="super_admin")

        with pytest.raises(ProtectedPermissionError):
            await handler.handle(
                DeletePermissionCommand(
                    name="system:manage_settings",
                    user_jwt_data=user_jwt_data
                )
            )

        assert permission_blacklist.get_permission_invalidation_time("system:manage_settings") is not None
        permission = await permission_repository.get_permission_by_name("system:manage_settings")
        assert permission is not None

