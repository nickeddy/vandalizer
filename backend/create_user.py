#!/usr/bin/env python3
"""Create a regular (non-admin) user account.

Idempotent: safe to re-run. If the user already exists, the password is reset
to the supplied value and name is updated.

Usage:
    cd backend
    USER_EMAIL=jane@example.com USER_PASSWORD=tempPassword python create_user.py

Environment variables (or .env file):
    USER_EMAIL     (required)
    USER_PASSWORD  (required)
    USER_NAME      (default: derived from email local-part)
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from app.config import Settings
from app.database import init_db
from app.models.user import User


async def ensure_user(email: str, password: str, name: str | None) -> tuple[User, str]:
    from app.utils.security import hash_password

    normalized_email = email.strip().lower()
    display_name = name or normalized_email.split("@", 1)[0]

    existing = await User.find_one(User.email == normalized_email)
    if existing:
        existing.password_hash = hash_password(password)
        if name:
            existing.name = display_name
        await existing.save()
        return existing, "updated"

    from app.services.auth_service import register

    user = await register(
        user_id=normalized_email,
        email=normalized_email,
        password=password,
        name=display_name,
    )
    return user, "created"


async def main():
    settings = Settings()
    await init_db(settings)

    email = os.environ.get("USER_EMAIL", "")
    password = os.environ.get("USER_PASSWORD", "")
    name = os.environ.get("USER_NAME", "") or None

    if not email or not password:
        print("Error: USER_EMAIL and USER_PASSWORD environment variables are required.")
        print("Usage: USER_EMAIL=jane@example.com USER_PASSWORD=secret python create_user.py")
        sys.exit(1)

    user, status = await ensure_user(email, password, name)

    if status == "updated":
        print(f"Updated existing user '{user.user_id}' (password reset).")
        return

    print("Created user:")
    print(f"  Email: {email.strip().lower()}")
    print(f"  Name:  {user.name}")


if __name__ == "__main__":
    asyncio.run(main())
