# models/File.py

from typing import List
from uuid import uuid4
from sqlalchemy import Column, String, ForeignKey, DateTime
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, default=lambda: str(uuid4()), unique=True, nullable=False,)
    file_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="files")
    versions: Mapped[List["FileVersion"]] = relationship(
        "FileVersion",
        back_populates="version_file",
        cascade="all, delete-orphan",
        order_by="FileVersion.version_number",
        lazy="selectin"
    )
