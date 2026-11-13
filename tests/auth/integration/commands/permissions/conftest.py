import pytest

from app.auth.models.permission import Permission


@pytest.fixture
def create_permissions(
    permission_repository,
    db_session
):
    async def create(
        names: set[str]
    ):
        for name in names:
            await permission_repository.create(
                Permission(name=name)
            )
        await db_session.commit()

    return create
