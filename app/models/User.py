# models/User.py

from datetime import datetime, timezone
from typing import List
from sqlalchemy import Column, DateTime, String, Boolean
from uuid import uuid4
from passlib.context import CryptContext
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.File import File

pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, unique=True, nullable=False, default=lambda: str(uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    files: Mapped[List["File"]] = relationship("File", back_populates="owner", cascade="all, delete-orphan")

    def verify_password(self, plain_password:str)->bool:
        return pwd_context.verify(plain_password, self.password)

    def to_jwt_payload(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
        }

    @staticmethod
    def hash_password(password:str)->str:
        return pwd_context.hash(password)
