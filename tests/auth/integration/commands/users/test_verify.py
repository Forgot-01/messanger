import hashlib
from datetime import timedelta

import pytest
from dishka import AsyncContainer

from app.auth.commands.users.verify import VerifyCommand, VerifyCommandHandler
from app.core.services.auth.exceptions import InvalidTokenError


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestVerifyCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> VerifyCommandHandler:
        return await request_container.get(VerifyCommandHandler)

    @pytest.fixture
    async def get_verify_code(
        self,
        token_blacklist_repository,
        create_user,
    ) -> tuple[str, int]:
        user = await create_user()

        verify_code = "0001"
        hashed_token = hashlib.sha256(verify_code.encode()).hexdigest()
        await token_blacklist_repository.add_code(
            hashed_token,
            user_id=user.id,
            expiration=timedelta(minutes=1)
        )
        return verify_code, user.id

    async def test_verify_success(
        self, handler, get_verify_code, user_repository
    ) -> None:
        verify_code, user_id = get_verify_code

        await handler.handle(
            VerifyCommand(
                token=verify_code
            )
        )

        user = await user_repository.get_by_id(user_id)
        assert user
        assert user.is_verified

        with pytest.raises(InvalidTokenError):
            await handler.handle(
                VerifyCommand(
                    token=verify_code
                )
            )
