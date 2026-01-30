from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_password_hash
from db.models.users import Role, User, UserRole

fake = Faker()


class UserFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        email: str | None = None,
        username: str | None = None,
        password: str = "testpass123",
        roles: list[str] | None = None,
        **kwargs,
    ) -> User:
        user = User(
            email=email or fake.email(),
            username=username or fake.user_name()[:50],
            password_hash=get_password_hash(password),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            country_code="PT",
            is_active=True,
            is_verified=True,
            **kwargs,
        )
        db.add(user)
        await db.flush()

        if roles:
            for role_name in roles:
                role = await db.execute(select(Role).where(Role.name == role_name))
                role = role.scalar_one_or_none()
                if role:
                    user_role = UserRole(user_id=user.id, role_id=role.id)
                    db.add(user_role)

        await db.commit()
        await db.refresh(user)
        return user
