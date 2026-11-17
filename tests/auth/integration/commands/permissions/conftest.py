import pytest

from app.auth.models.permission import Permission
from app.auth.models.user import User


@pytest.fixture
def create_permissions(
    permission_repository,
    db_session
):
    async def create(
        names: set[str], user: User | None=None
    ):
        for name in names:
            perm = Permission(name=name)
            await permission_repository.create(perm)

            if user:
                user.add_permission(perm)

        await db_session.commit()

    return create
