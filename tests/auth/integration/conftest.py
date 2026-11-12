import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.commands.auth.login import LoginCommandHandler
from app.auth.dtos.user import AuthUserJWTData
from app.auth.models.permission import Permission
from app.auth.models.role import Role
from app.auth.models.user import User
from app.auth.repositories.permission import PermissionRepository
from app.auth.repositories.role import RoleRepository
from app.auth.repositories.user import UserRepository
from app.auth.services.hash import HashService
from tests.auth.integration.utils import create_login_command


async def _require_role(role_repository: RoleRepository, name: str) -> Role:
    role = await role_repository.get_with_permission_by_name(name)
    if role is None:
        pytest.fail(
            f"Role {name!r} not found; ensure session seed data (create_first_data) ran."
        )
    return role


async def _require_permission(
    permission_repository: PermissionRepository,
    permission_names: set[str] | None
) -> set[Permission]:
    if permission_names is None:
        return set()

    permissions = await permission_repository.get_permissions_by_names(permission_names)
    return set(permissions)


@pytest.fixture
def create_user(
    db_session: AsyncSession,
    user_repository: UserRepository,
    hash_service: HashService,
    role_repository: RoleRepository,
    permission_repository,
):
    async def _create(
        email: str = "base@gmail.com",
        username: str = "standartser",
        password: str = "TestPass123!",
        is_verified: bool = False,
        role_name: str = "user",
        permission_names: set[str] | None=None
    ) -> User:
        role = await _require_role(role_repository, role_name)
        permissions = await _require_permission(permission_repository, permission_names)
        user = User.create(
            email=email,
            username=username,
            password_hash=hash_service.hash_password(password),
            is_verified=is_verified,
            roles={role},
            permissions=permissions
        )

        await user_repository.create(user)
        await db_session.commit()

        return user

    return _create


@pytest.fixture
def auth_headers(create_access_token):
    def _headers(user: User) -> dict[str, str]:
        token = create_access_token(user)
        return {"Authorization": f"Bearer {token}"}

    return _headers

@pytest.fixture
def get_user_and_token_group(
    create_user,
    request_container,
):
    async def create(
        email: str = "base@gmail.com",
        username: str = "standartser",
        password: str = "TestPass123!",
        is_verified: bool = False,
        role_name: str = "user",
        permission_names: set[str] | None=None,
    ):
        user = await create_user(
            email=email,
            username=username,
            password=password,
            is_verified=is_verified,
            role_name=role_name,
            permission_names=permission_names
        )
        login_handler = await request_container.get(LoginCommandHandler)

        token_group = await login_handler.handle(
            create_login_command(
                username=username,
                password=password,
            )
        )
        return user, token_group
    return create


@pytest.fixture
def get_user_jwt_data(
    create_user,
):
    async def create(
        email: str = "base@gmail.com",
        username: str = "standartser",
        password: str = "TestPass123!",
        is_verified: bool = False,
        role_name: str = "user",
        permission_names: set[str] | None=None,
    ):

        user = await create_user(
            email=email,
            username=username,
            password=password,
            is_verified=is_verified,
            role_name=role_name,
            permission_names=permission_names
        )
        return user, AuthUserJWTData.create_from_user(user=user, device_id="1", session_id="1")

    return create

