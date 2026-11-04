from dataclasses import dataclass
from uuid import UUID

from app.auth.models.device import Device
from app.auth.models.session import Session
from app.auth.repositories.device import UserDeviceRepository
from app.auth.repositories.session import SessionRepository


@dataclass
class DeviceSessionManager:
    device_repository: UserDeviceRepository
    session_repository: SessionRepository

    async def get_or_create_session(
        self,
        user_id: int,
        did: str,
        device_name: str,
        platform: str,

        os_version: str | None,
        app_version: str | None,
        fcm_token: str,
        ip_address: str,
        user_agent: str,
    ) -> tuple[Device, Session]:
        device = await self.device_repository.get_by_user_device_id(
            user_id=user_id, device_id=did
        )
        if device is None:
            device = Device.create(
                user_id=user_id, did=did,
                device_name=device_name, platform=platform,
                os_version=os_version, app_version=app_version,
                fcm_token=fcm_token
            )

            session = Session.create(
                user_id=user_id,
                device_id=device.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.online()
            await self.session_repository.create(session=session)
            await self.device_repository.create(device=device)
            return device, session


        old_session = await self.session_repository.get_active_by_device(
            user_id=user_id, device_id=device.id
        )
        if old_session is not None:
            old_session.deactivate()

        session = Session.create(
            user_id=user_id,
            device_id=device.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.online()
        return device, session

    async def get_user_session(
        self, user_id: int, device_id: UUID
    ) -> Session | None:
        active_session = await self.session_repository.get_active_by_device(
            user_id=user_id,
            device_id=device_id,
        )

        if active_session:
            active_session.online()
            return active_session

        return active_session

