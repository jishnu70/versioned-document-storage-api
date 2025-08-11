from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, func, case
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
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
    # If content is given, hash it for comparison
    hashed_content = hash_bytes(content) if content else None

    # Start query: find files by user and file name
    query = (
        select(
            File,
            # to find the last version number
            func.max(FileVersion.version_number).label("last_version"),
            # to check if version is duplicate
            func.bool_or(FileVersion.check_sum==hashed_content if hashed_content else False).label("is_duplicate")
        )
        .join(FileVersion, File.id==FileVersion.file_id, isouter=True)
        .where(
            File.user_id==user_id,
            File.file_name==filename
        )
        .group_by(File.created_at)
    )
    result = await db.execute(query)
    row = result.first()
    # CASE 1: No file at all
    if not row:
        return None, False, 0  # brand new file
    file_obj, last_version_number, is_duplicate = row
    return file_obj, is_duplicate, last_version_number

async def fetch_file_or_version(db: AsyncSession, owner_id: str, file_name: str, version_id: Optional[str]=None):
    """
    fetch file with it's version ID
    if version_id is not given, return the fileversion which is marked is_current
    if given version_id does not exist, return the fileversion which is marked is_current
    """

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
        FileVersion,
        File.id==FileVersion.file_id,
        isouter=True
    ).where(and_(File.user_id==owner_id, File.file_name==file_name)
    ).order_by(priority).limit(1)

    result = await db.execute(query)
    data = result.scalars().first()

    return data

async def create_new_file(db: AsyncSession, user_id: str, filename: str):
    """Create new file ID only if it does not exist."""
    new_file = File(file_name=filename,user_id = user_id)
    db.add(new_file)
    await db.flush()
    await db.refresh(new_file)
    return new_file

async def mark_previous_versions_not_current(db: AsyncSession, file_obj: File):
    """Mark all previous versions of a file as not current."""
    for version in file_obj.versions:
        version.is_current=False

async def create_new_file_version(db: AsyncSession, file_id: str, content: bytes, lvr: int, original_filename: str):
    """
    Save new version of the file.

    lvr = last_version_number
    """

    new_version = FileVersion(
        file_id=file_id,
        version_number=lvr+1,
        check_sum = hash_bytes(content),
        storage_path="",
        is_current=True
    )
    db.add(new_version)
    await db.flush(new_version)
    await db.refresh(new_version)

    # save file logic
    file_path = save_file_locally(file_id, new_version.id, content, original_filename)
    new_version.storage_path = file_path

    return new_version

async def save_file_service(db: AsyncSession, user_id: str, file: UploadFile):
    """actual save service"""

    filename = file.filename
    if not filename:
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail="Provide filename to the file")
    file_content = await file.read()

    try:
        file_obj, existing, lvr = await get_file_by_name_or_using_content(db, user_id, filename, file_content)

        # file does not exist
        if not file_obj:
            file_obj = await create_new_file(db, user_id, filename)
            lvr=0

        # version exist, avoid duplicating
        if existing:
            raise HTTPException(status.HTTP_208_ALREADY_REPORTED, detail="File is already saved")

        await mark_previous_versions_not_current(db, file_obj)

        # save the new version
        new_version = await create_new_file_version(db, file_obj.id, file_content, lvr, filename)

        await db.commit()

        return new_version.id
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error(f"Error saving file: {exc}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

async def get_local_file_path(db: AsyncSession, owner_id: str, file_name: str, version_id: Optional[str]=None):
    version = await fetch_file_or_version(db, owner_id, file_name, version_id)
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File name is wrong")

    file_path = fetch_local_file(version.file_id, version.id)
    return file_path
