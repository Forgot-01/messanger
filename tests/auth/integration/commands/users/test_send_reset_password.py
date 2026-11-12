
import pytest
from dishka import AsyncContainer

from app.auth.commands.users.send_reset_password import SendResetPasswordCommand, SendResetPasswordCommandHandler


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestSendResetPasswordCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> SendResetPasswordCommandHandler:
        return await request_container.get(SendResetPasswordCommandHandler)

    async def test_success_send_reset_password(
        self,
        handler,
        create_user,
        mock_mail_service,
    ) -> None:
        user = await create_user(email="test@gmail.com")

        await handler.handle(SendResetPasswordCommand(
            email=user.email
        ))

        assert len(mock_mail_service.sent_emails)
        assert mock_mail_service.sent_emails[0]["data"].recipient == "test@gmail.com"

