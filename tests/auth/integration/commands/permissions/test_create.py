import pytest
from dishka import AsyncContainer

from app.auth.commands.permissions.create import CreatePermissionCommand, CreatePermissionCommandHandler
from app.auth.exceptions import DuplicatePermissionError, ProtectedPermissionError
from app.core.services.auth.exceptions import AccessDeniedError


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestCreateCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> CreatePermissionCommandHandler:
        return await request_container.get(CreatePermissionCommandHandler)


    async def test_create_sccess(
        self, handler, get_user_jwt_data,
        permission_repository
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data(role_name="super_admin")

        await handler.handle(
            CreatePermissionCommand(
                name="new:permission",
                user_jwt_data=user_jwt_data
            )
        )

        permission = await permission_repository.get_permission_by_name("new:permission")
        assert permission
        assert permission.name == "new:permission"


    async def test_create_error(
        self, handler, get_user_jwt_data
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data()

        with pytest.raises(AccessDeniedError):
            await handler.handle(
                CreatePermissionCommand(
                    name="new:permission",
                    user_jwt_data=user_jwt_data
                )
            )

        user_jwt_data.permissions.extend(["permission:create", "user:create"])

        with pytest.raises(ProtectedPermissionError):
            await handler.handle(
                CreatePermissionCommand(
                    name="permission:create",
                    user_jwt_data=user_jwt_data
                )
            )

        with pytest.raises(DuplicatePermissionError):
            await handler.handle(
                CreatePermissionCommand(
                    name="user:create",
                    user_jwt_data=user_jwt_data
                )
            )
