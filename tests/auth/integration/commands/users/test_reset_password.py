import hashlib
from datetime import timedelta

import pytest
from dishka import AsyncContainer

from app.auth.commands.users.reset_password import ResetPasswordCommand, ResetPasswordCommandHandler
from app.auth.exceptions import PasswordMismatchError
from app.core.services.auth.exceptions import InvalidTokenError
from app.core.utils import fromtimestamp


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestSendResetPasswordCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> ResetPasswordCommandHandler:
        return await request_container.get(ResetPasswordCommandHandler)

    @pytest.fixture
    async def get_reset_password_code(
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
            expiration=timedelta(minutes=1),
            type_code="reset_password"
        )
        return verify_code, user.id

    async def test_reset_password_success(
        self, handler, get_reset_password_code, user_repository, hash_service,
        token_blacklist_repository,
    ) -> None:
        reset_code, user_id = get_reset_password_code

        await handler.handle(
            ResetPasswordCommand(
                token=reset_code,
                password="NewPass1234!",
                password_repeat="NewPass1234!",
            )
        )

        user = await user_repository.get_by_id(user_id)
        assert user
        assert hash_service.verify_password("NewPass1234!", user.password_hash)
        assert await token_blacklist_repository.get_user_blacklist(user_id) != fromtimestamp(float("0"))

        with pytest.raises(InvalidTokenError):
            await handler.handle(
                ResetPasswordCommand(
                    token=reset_code,
                    password="NewPass1234!",
                    password_repeat="NewPass1234!",
                )
            )

    async def test_reset_password_mismatch(
        self, handler, get_reset_password_code, token_blacklist_repository
    ) -> None:
        reset_code, user_id = get_reset_password_code

        with pytest.raises(PasswordMismatchError):
            await handler.handle(
                ResetPasswordCommand(
                    token=reset_code,
                    password="NewPass1234!",
                    password_repeat="PasswordMismatch1234!",
                )
            )

        assert await token_blacklist_repository.get_user_blacklist(user_id) == fromtimestamp(float("0"))
