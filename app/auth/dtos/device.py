from pydantic import BaseModel, ConfigDict


class DeviceInfo(BaseModel):
    device_id: str
    platform: str
    device_name: str

    os_version: str | None
    app_version: str | None
    fcm_token: str

    model_config = ConfigDict(from_attributes=True)


class AuthInfo(BaseModel):
    device: DeviceInfo
    ip_address: str
    user_agent: str

