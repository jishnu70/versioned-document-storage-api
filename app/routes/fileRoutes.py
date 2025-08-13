# routes/fileRoutes.py

from typing import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.User import get_current_user
from app.models.User import User
from app.schemas.FileSchemas import AllFileResponse, FileVersionSchema
from app.service.File_service import fetch_file_or_version, get_all_files_of_the_user, get_all_versions_of_file, get_local_file_path, save_file_service
import logging

logger = logging.getLogger(__name__)

file_router = APIRouter(
    prefix="/file",
    tags=["file"],
)

@file_router.get("/", response_model=AllFileResponse)
async def get_all_files_of_user(user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        result = await get_all_files_of_the_user(db, user.id)

        if result is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No Files Saved by the user")

        return AllFileResponse(files=result)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

@file_router.get("/{file_name}", response_model=list[FileVersionSchema])
async def get_file_by_name(user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)], file_name: str, all: bool=False):
    try:
        if all:
            result = await get_all_versions_of_file(db, user.id, file_name)
        else:
            single = await fetch_file_or_version(db, user.id, file_name)
            result = [single] if single else None

        if result is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invalid file name")

        return result
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="error occurred")

@file_router.get("/{file_name}/{version_id}")
async def get_file_by_version(user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)], file_name: str, version_id: str):
    try:
        result = await get_local_file_path(db, user.id, file_name, version_id)

        if result is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="error in the storage")

        return FileResponse(result)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="error occurred")

@file_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_file_version(file: Annotated[UploadFile, File(...)], user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        result = await save_file_service(db, user.id, file)
        return {"message": "Successfully file saved", "version_id": result}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise
