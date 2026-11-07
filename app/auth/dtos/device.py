from pydantic import BaseModel, ConfigDict


class DeviceInfo(BaseModel):
    device_id: str
    device_name: str
    platform: str

    os_version: str | None
    app_version: str | None
    fcm_token: str | None

    model_config = ConfigDict(from_attributes=True)


class OAuthInfo(BaseModel):
    device: DeviceInfo
    user_id: int | None
    ip_address: str
    user_agent: str
    code_verifier: str
    provider: str
