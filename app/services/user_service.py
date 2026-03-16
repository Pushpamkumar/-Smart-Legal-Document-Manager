from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user(self, name: str, email: str) -> User:
        user = self.db.scalar(select(User).where(User.email == email))
        if user:
            if user.name != name:
                user.name = name
                self.db.flush()
            return user

        user = User(name=name, email=email)
        self.db.add(user)
        self.db.flush()
        return user

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))
