import base64
import hashlib
import secrets
from dataclasses import dataclass, field

from app.auth.dtos.tokens import OAuthData
from app.auth.exceptions import NotExistProviderOAuthError, OAuthProviderUnavailableError
from app.auth.services.oauth_providers import OAuthProvider
from app.core.exceptions import ApplicationError


@dataclass
class OAuthProviderFactory:
    providers: dict[str, OAuthProvider] = field(default_factory=dict)

    def get_provider(self, provider_name: str) -> OAuthProvider:
        provider = self.providers.get(provider_name)
        if not provider:
            raise NotExistProviderOAuthError(provider=provider_name)
        return provider

    def register_provider(self, provider: OAuthProvider) -> None:
        self.providers[provider.name] = provider


@dataclass
class OAuthManager:
    provider_factory: OAuthProviderFactory

    async def get_authorize_url(
        self,
        provider_name: str,
        state: str,
        code_challenge: str,
    ) -> str:
        provider = self.provider_factory.get_provider(provider_name)
        return provider.get_auth_url(state, code_challenge=code_challenge)

    async def process_callback(
        self,
        provider_name: str,
        code: str,
        code_verifier: str,
    ) -> OAuthData:
        provider = self.provider_factory.get_provider(provider_name)

        try:
            token = await provider.exchange_code_for_token(
                code=code,
                code_verifier=code_verifier,
            )
            oauth_user = await provider.get_user_info(token.access_token)
        except ApplicationError:
            raise
        except Exception as err:
            raise OAuthProviderUnavailableError(provider=provider_name) from err

        return oauth_user

    def generate_state(self) -> str:
        return secrets.token_urlsafe(32)

    def generate_code_verifier(self) -> str:
        return secrets.token_urlsafe(64)

    def generate_code_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(
            verifier.encode("ascii")
        ).digest()

        return base64.urlsafe_b64encode(
            digest
        ).rstrip(b"=").decode("ascii")
