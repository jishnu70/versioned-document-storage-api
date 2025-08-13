from pydantic import BaseModel
from datetime import datetime

class FileVersionSchema(BaseModel):
    id: str
    version_number: int
    is_current: bool
    created_at: datetime

    class Config:
        from_attributes = True  # Allows reading from SQLAlchemy models

class FileSchema(BaseModel):
    id: str
    file_name: str
    created_at: datetime
    versions: list[FileVersionSchema]

    class Config:
        from_attributes = True

class AllFileResponse(BaseModel):
    files: list[FileSchema]
