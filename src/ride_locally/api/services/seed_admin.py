from argon2 import PasswordHasher
from sqlalchemy import select

from ride_locally.config import config
from ride_locally.db.schema import ApiUserTable
from ride_locally.db.session import session

ph = PasswordHasher()


async def seed_admin_user():
    async with session() as s:
        result = await s.execute(
            select(ApiUserTable).where(ApiUserTable.email == config.API_ADMIN_EMAIL)
        )
        admin = result.scalar_one_or_none()

        if admin is None:
            s.add(
                ApiUserTable(
                    email=config.API_ADMIN_EMAIL,
                    username=config.API_ADMIN_USERNAME,
                    password_hash=ph.hash(config.API_ADMIN_PASSWORD),
                )
            )
        await s.commit()
