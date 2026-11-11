from dishka import AsyncContainer
import pytest

from app.auth.commands.users.verify import VerifyCommand, VerifyCommandHandler


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

    # async def test_verify_success(
    #     self, handler, token_blacklist_repository,
    # ) -> None:

    #     await handler.handle(
    #         VerifyCommand(
    #             token=""
    #         )
    #     )

