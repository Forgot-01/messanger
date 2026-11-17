from dishka import AsyncContainer
import pytest

from app.auth.commands.roles.create import CreateRoleCommand, CreateRoleCommandHandler
from app.auth.exceptions import DuplicateRoleError, NotFoundPermissionsError


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestCreateRoleCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> CreateRoleCommandHandler:
        return await request_container.get(CreateRoleCommandHandler)

    async def test_create_role(
        self, handler, get_user_jwt_data, role_repository
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data(role_name="super_admin")

        await handler.handle(
            CreateRoleCommand(
                role_name="Test",
                description="test for test",
                security_level=9,
                permissions=set(),
                user_jwt_data=user_jwt_data
            )
        )

        role = await role_repository.get_with_permission_by_name("Test")
        assert role is not None
        assert role.security_level == 9
        assert len(role.permissions) == 0


    async def test_errors(
        self, handler, get_user_jwt_data, role_repository
    ) -> None:
        user, user_jwt_data = await get_user_jwt_data(role_name="super_admin")

        with pytest.raises(DuplicateRoleError):
            await handler.handle(
                CreateRoleCommand(
                    role_name="super_admin",
                    description="test for test",
                    security_level=9,
                    permissions=set(),
                    user_jwt_data=user_jwt_data
                )
            )

        with pytest.raises(NotFoundPermissionsError):
            await handler.handle(
                CreateRoleCommand(
                    role_name="Tets",
                    description="test for test",
                    security_level=9,
                    permissions={"permission:not_found", },
                    user_jwt_data=user_jwt_data
                )
            )