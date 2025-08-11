# models/FileVersion.py

from uuid import uuid4
from sqlalchemy import Boolean, Column, String, ForeignKey, DateTime, Integer
from datetime import datetime, timezone
from app.models.File import File
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.utils.hash_util import hash_bytes
from app.database import Base

class FileVersion(Base):
    __tablename__ = "file_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, default=lambda: str(uuid4()), unique=True, nullable=False,)
    file_id: Mapped[str] = mapped_column(String, ForeignKey("files.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    check_sum: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    version_file: Mapped["File"] = relationship("File", back_populates="versions")

    @staticmethod
    def hash_file_contents(content: bytes)->str:
        return hash_bytes(content)
