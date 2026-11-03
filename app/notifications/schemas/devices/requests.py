from pydantic import BaseModel


class CreateUserDeviceRequest(BaseModel):
    platform: str
    token: str
    device_name: str

