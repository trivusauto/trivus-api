import asyncio
import uuid
from sqlalchemy import select
from src.modules.auth.infrastructure.orm import UserModel
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.shared.infrastructure.database import SessionFactory


async def main() -> None:
    email, password = "admin@trivus.local", "admin123"
    async with SessionFactory() as s:
        exists = (await s.execute(select(UserModel).where(UserModel.email == email))).scalar_one_or_none()
        if not exists:
            s.add(UserModel(id=str(uuid.uuid4()), email=email, name="Admin Trivus", role="admin",
                            active=True, password_hash=Argon2PasswordHasher().hash(password)))
            await s.commit()
    print(f"Seeded admin: {email}")


if __name__ == "__main__":
    asyncio.run(main())
