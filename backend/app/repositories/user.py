"""Repository utilisateurs (chargement avec rôle pour le RBAC)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(
            select(User).options(selectinload(User.role)).where(User.email == email)
        )

    async def get_with_role(self, user_id: int) -> User | None:
        return await self.session.scalar(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
