import pytest
from dishka import AsyncContainer

from app.auth.commands.users.send_verify import SendVerifyCommand, SendVerifyCommandHandler


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestSendVerifyCommand:

    @pytest.fixture
    async def handler(
        self,
        request_container: AsyncContainer
    ) -> SendVerifyCommandHandler:
        return await request_container.get(SendVerifyCommandHandler)


    async def test_send_verify(
        self,
        handler,
        create_user,
        mock_mail_service,
    ) -> None:
        user = await create_user(email="test@gmail.com")

        await handler.handle(SendVerifyCommand(
            email=user.email
        ))

        assert len(mock_mail_service.sent_emails)
        assert mock_mail_service.sent_emails[0]["data"].recipient == "test@gmail.com"

    async def test_send_verify_fake_email(
        self,
        handler,
        mock_mail_service,
    ) -> None:
        await handler.handle(SendVerifyCommand(
            email="fake@gmail.com"
        ))
        await handler.handle(SendVerifyCommand(
            email="fake1@gmail.com"
        ))

        assert len(mock_mail_service.sent_emails) == 0

