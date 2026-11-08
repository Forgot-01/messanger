from typing import Literal

from pydantic import BaseModel


class CreateUserDeviceRequest(BaseModel):
    platform: Literal["ANDROID", "IOS", "WINDOWS", "LINUX"]
    token: str
    device_name: str

