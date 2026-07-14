import asyncio
from app.core.database.session import get_session
from app.modules.employee.models.organization import Organization
from app.modules.rbac.models.user import User
from app.modules.rbac.models.membership import UserOrganizationMembership
from app.core.security.password import hash_password

async def main():
    async with get_session() as session:
        # Check or create Organization 1
        org = await session.get(Organization, 1)
        if not org:
            org = Organization(
                org_id=1,
                org_code="ORG1",
                org_name="Test Organization",
                is_active=True,
                is_deleted=False
            )
            session.add(org)
            await session.flush()
            print("Seeded Organization ID 1")
        else:
            print("Organization ID 1 already exists")

        # Check or create User
        from sqlalchemy import select
        stmt = select(User).where(User.org_id == 1, User.email == "user@example.com")
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            user = User(
                id=1,
                org_id=1,
                name="Test User",
                email="user@example.com",
                mobile_country_code="+91",
                mobile_number="9876543210",
                password_hash=hash_password("Secret123"),
                is_super_admin=True,
                is_active=True
            )
            session.add(user)
            await session.flush()
            print("Seeded User ID 1 (user@example.com / Secret123)")
        else:
            print("User user@example.com already exists")

        # Seed membership
        stmt_mem = select(UserOrganizationMembership).where(
            UserOrganizationMembership.user_id == user.id,
            UserOrganizationMembership.org_id == 1
        )
        res_mem = await session.execute(stmt_mem)
        mem = res_mem.scalar_one_or_none()

        if not mem:
            mem = UserOrganizationMembership(
                user_id=user.id,
                org_id=1,
                is_primary=True,
                is_active=True
            )
            session.add(mem)
            await session.flush()
            print("Seeded UserOrganizationMembership for User ID 1 and Org ID 1")
        else:
            print("Membership already exists")

if __name__ == "__main__":
    asyncio.run(main())
