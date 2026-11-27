import asyncio
from dataclasses import dataclass

from passlib.context import CryptContext


@dataclass
class HashService:
    pwd_context: CryptContext

    async def hash_password(self, password: str) -> str:
        return await asyncio.to_thread(self.pwd_context.hash, password)

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return await asyncio.to_thread(
            self.pwd_context.verify, plain_password, hashed_password
        )


