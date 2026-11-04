from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import select

from app.auth.models.device import Device
from app.core.db.repository import IRepository


@dataclass
class UserDeviceRepository(IRepository[Device]):
    redis: Redis

    async def create(self, device: Device) -> None:
        self.session.add(device)

    async def get_by_user_device_id(self, user_id: int, device_id: str) -> Device | None:
        stmt = select(Device).where(
            Device.user_id==user_id, Device.did==device_id
        )
        result = await self.session.execute(stmt)
        return result.scalar()

