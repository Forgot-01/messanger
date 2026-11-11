from uuid import uuid4

from app.auth.commands.auth.login import LoginCommand


def create_login_command(
        username: str,
        password: str,
        device_id: str | None = None,
        platform: str = "windows",
        device_name: str = "msi katana",
        os_version: str | None = None,
        app_version: str | None = None,
        fcm_token: str | None = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = "Chrome"
    ) -> LoginCommand:
        return LoginCommand(
            username=username,
            password=password,
            device_id=device_id or str(uuid4()),
            platform=platform,
            device_name=device_name,
            os_version=os_version,
            app_version=app_version,
            fcm_token=fcm_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )
