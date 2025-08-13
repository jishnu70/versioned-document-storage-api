# service/File_service.py

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, func, case, Integer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.config import config
from app.models.User import User
from app.models.File import File
from app.models.FileVersion import FileVersion
from app.utils.hash_util import hash_bytes
import logging
from typing import Optional
from app.infrastructure.file_storage import save_file_locally
from app.infrastructure.file_storage import fetch_local_file

logger = logging.getLogger(__name__)

async def get_file_by_name_or_using_content(
    db: AsyncSession,
    user_id: str,
    filename: str,
    content: Optional[bytes]=None
):
    logger.info("Checking for existing file with name: %s", filename)
    # If content is given, hash it for comparison
    hashed_content = await hash_bytes(content) if content else None

    # Start query: find files by user and file name
    query = (
        select(
            File,
            # to find the last version number
            #func.max(FileVersion.version_number).label("last_version"),
            # to check if version is duplicate
            #func.max((FileVersion.check_sum == hashed_content).cast(Integer)).label("is_duplicate")
            # func.bool_or(FileVersion.check_sum==hashed_content if hashed_content else False).label("is_duplicate")
        )
        # .join(FileVersion, File.id == FileVersion.file_id, isouter=True)
        .where(File.user_id == user_id, File.file_name == filename)
        .group_by(File.id)  # group by primary key
        .options(selectinload(File.versions))  # preload versions
    )
    result = await db.execute(query)
    row = result.scalars().first()
    # CASE 1: No file at all
    if not row:
        logger.info("No existing file found")
        return None, False, 0  # brand new file
    file_obj = row
    if file_obj:
        last_version = max((v.version_number for v in file_obj.versions), default=0)
        is_duplicate = any(v.check_sum == hashed_content for v in file_obj.versions)
    else:
        last_version = 0
        is_duplicate = False
    logger.info("Found file with ID: %s, is_duplicate: %s, last_version: %s", file_obj.id, is_duplicate, last_version)
    return file_obj, is_duplicate, last_version

async def fetch_file_or_version(db: AsyncSession, owner_id: str, file_name: str, version_id: Optional[str]=None):
    """
    fetch file with it's version ID
    if version_id is not given, return the fileversion which is marked is_current
    if given version_id does not exist, return the fileversion which is marked is_current
    """
    logger.info("Fetching file or version for owner: %s, file_name: %s, version_id: %s", owner_id, file_name, version_id)
    if version_id:
        priority = case(
            (FileVersion.id==version_id, 1),
            (FileVersion.is_current==True, 2),
            else_=3
        )
    else:
        priority = case(
            (FileVersion.is_current==True,1),
            else_=2
        )
    query = select(FileVersion).join(
        File,
        File.id==FileVersion.file_id,
        isouter=True
    ).where(and_(File.user_id==owner_id, File.file_name==file_name)
    ).order_by(priority).limit(1)

    result = await db.execute(query)
    data = result.scalars().first()
    logger.info("Fetch result: %s", data)
    return data

async def create_new_file(db: AsyncSession, user_id: str, filename: str):
    """Create new file ID only if it does not exist."""
    logger.info("Creating new file with name: %s for user: %s", filename, user_id)
    new_file = File(file_name=filename,user_id = user_id)
    db.add(new_file)
    await db.flush()
    await db.refresh(new_file)
    logger.info("New file created with ID: %s", new_file.id)
    return new_file

async def mark_previous_versions_not_current(db: AsyncSession, file_obj: File):
    """Mark all previous versions of a file as not current."""
    logger.info("Marking previous versions as not current for file ID: %s", file_obj.id)
    if file_obj.versions:  # list is loaded
        for v in file_obj.versions:
            v.is_current = False
    await db.flush()
    logger.info("Previous versions marked as not current")

async def create_new_file_version(db: AsyncSession, file_id: str, content: bytes, lvr: int, original_filename: str):
    """
    Save new version of the file.

    lvr = last_version_number
    """
    logger.info("Creating new file version")
    new_version = FileVersion(
        file_id=file_id,
        version_number=lvr+1,
        check_sum = await hash_bytes(content),
        storage_path="",
        is_current=True
    )
    db.add(new_version)
    logger.info("Flushing new version to database")
    await db.flush()
    logger.info("Refreshing new version")
    await db.refresh(new_version)

    # save file logic
    logger.info("New version flushed with ID: %s", new_version.id)

    logger.info("Saving file locally for version ID: %s", new_version.id)
    file_path = await save_file_locally(file_id, new_version.id, content, original_filename)
    new_version.storage_path = file_path
    logger.info(f"File saved at: {file_path}")

    return new_version

async def save_file_service(db: AsyncSession, user_id: str, file: UploadFile):
    """actual save service"""
    logger.info("Starting file save service for user: %s", user_id)
    filename = file.filename
    if not filename:
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail="Provide filename to the file")

    max_file_size = config.MAX_FILE_SIZE
    if not file.size or file.size > max_file_size:
        raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds limit of {max_file_size // (1024 * 1024)} MB"
            )
    file_content = await file.read()
    logger.info("File content read, size: %s bytes", len(file_content))
    try:
        logger.info("Checking for existing file")
        file_obj, existing, lvr = await get_file_by_name_or_using_content(db, user_id, filename, file_content)
        logger.info("File check result - exists: %s, last_version: %s", existing, lvr)

        # file does not exist
        if not file_obj:
            logger.info("Creating new file")
            file_obj = await create_new_file(db, user_id, filename)
            lvr=0

        # version exist, avoid duplicating
        if existing:
            logger.warning("File already exists with same content")
            raise HTTPException(status.HTTP_409_CONFLICT, detail="File is already saved")

        logger.info("Marking previous versions as not current")
        if file_obj and file_obj.versions:
            await mark_previous_versions_not_current(db, file_obj)

        # save the new version
        logger.info("Creating new file version")
        new_version = await create_new_file_version(db, file_obj.id, file_content, lvr, filename)

        logger.info("Committing database transaction")
        await db.commit()
        logger.info("Transaction committed, version ID: %s", new_version.id)
        return new_version.id
    except SQLAlchemyError as exc:
        logger.info("Rolling back database transaction")
        await db.rollback()
        logger.error(f"Error saving file: {exc}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

async def get_local_file_path(db: AsyncSession, owner_id: str, file_name: str, version_id: Optional[str]=None):
    version = await fetch_file_or_version(db, owner_id, file_name, version_id)

    if not version:
        return None

    file_path = await fetch_local_file(version.storage_path)

    return file_path

async def get_all_files_of_the_user(db: AsyncSession, owner_id: str):
    query = select(User).options(selectinload(User.files)).filter_by(id=owner_id)
    result = await db.execute(query)
    user = result.scalars().first()

    all_files = user.files if user else None

    return all_files

async def get_all_versions_of_file(db: AsyncSession, owner_id: str, file_name: str):
    query = select(File).options(selectinload(File.versions)).filter_by(user_id=owner_id, file_name=file_name)
    result = await db.execute(query)
    file_obj = result.scalars().first()
    file_versions = file_obj.versions if file_obj else None

    return file_versions
