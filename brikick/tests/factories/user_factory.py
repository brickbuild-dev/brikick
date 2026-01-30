from __future__ import annotations

from datetime import datetime, timezone

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.users import Role, User, UserRole

faker = Faker()


class UserFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        roles: list[str] | None = None,
        **kwargs,
    ) -> User:
        email = kwargs.pop("email", faker.unique.email())
        username = kwargs.pop("username", faker.unique.user_name()[:50])
        user = User(
            email=email,
            username=username,
            password_hash=kwargs.pop("password_hash", "test-hash"),
            first_name=kwargs.pop("first_name", faker.first_name()),
            last_name=kwargs.pop("last_name", faker.last_name()),
            country_code=kwargs.pop("country_code", "PT"),
            preferred_currency_id=kwargs.pop("preferred_currency_id", 978),
            is_active=kwargs.pop("is_active", True),
            is_verified=kwargs.pop("is_verified", True),
            last_login_at=kwargs.pop("last_login_at", None),
        )
        db.add(user)
        await db.flush()

        if roles:
            for role_name in roles:
                role_stmt = select(Role).where(Role.name == role_name)
                role_result = await db.execute(role_stmt)
                role = role_result.scalars().first()
                if role is None:
                    role = Role(name=role_name, description=None)
                    db.add(role)
                    await db.flush()
                user_role = UserRole(
                    user_id=user.id,
                    role_id=role.id,
                    granted_at=datetime.now(timezone.utc),
                    granted_by=None,
                )
                db.add(user_role)

        await db.flush()
        return user
