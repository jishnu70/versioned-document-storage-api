from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.models.File import File
from app.models.FileVersion import FileVersion
from app.utils.hash_util import hash_bytes
import logging

logger = logging.getLogger(__name__)

async def _commit_or_rollback(db: AsyncSession, route:str="DB"):
    """Commit DB changes, rollback if error."""
    try:
        await db.commit()
    except Exception as e:
        logger.error(f"Error in {route}: {str(e)}")
        await db.rollback()
        raise

async def get_file_by_name_or_using_content(
    db: AsyncSession,
    user_id: str,
    filename: str,
    content: bytes|None=None
):
    # If content is given, hash it for comparison
    hashed_content = hash_bytes(content) if content else None

    # Start query: find files by user and file name
    query = (
        select(File)
        .where(
            File.user_id==user_id,
            File.file_name==filename
        )
        .options(joinedload(File.versions))
    )
    result = await db.execute(query)
    row = result.scalars().first()

    # CASE 1: No file at all
    if not row:
        return None, False, 0  # brand new file

    file_obj = row
    check_sums = {version.check_sum for version in file_obj.versions if version.check_sum is not None}
    last_version_number: int = file_obj.versions[-1].version_number

    # if content not given
    if not hashed_content:
        return file_obj, False, last_version_number

    # check if version exists
    is_duplicate = (hashed_content in check_sums)
    return file_obj, is_duplicate, last_version_number

async def create_new_file(db: AsyncSession,user_id: str,filename: str):
    new_file = File(file_name=filename,user_id = user_id)
    db.add(new_file)
    try:
        await db.flush()
        await db.refresh(new_file)
        return new_file
    except SQLAlchemyError as exc:
        logger.error(f"Error in create new file: {str(exc)}")
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating new file")

async def handle_previous_versions(db: AsyncSession,user_id: str,filename: str):
    """Mark all previous versions of a file as not current."""
    existing_file, _, _ = await get_file_by_name_or_using_content(db, user_id, filename)
    if not existing_file:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File not found")

    for version in existing_file.versions:
        version.is_current=False

    await _commit_or_rollback(db, route="handle_previous_versions")

async def create_new_file_version(db: AsyncSession, file_id: str, content: bytes, lvr: int):
    # lvr = last_version_number

    # save file logic
    #
    new_version = FileVersion(
        file_id=file_id,
        version_number=lvr+1,
        check_sum = hash_bytes(content),
        storage_path="",
        is_current=True
    )
    db.add(new_version)
    await _commit_or_rollback(db, route="create_new_file_version")
    await db.refresh(new_version)

    await handle_previous_versions(
        db,
        new_version.version_file.user_id,
        new_version.version_file.file_name
    )
    return new_version.id

# actual save service
async def save_file_service(db: AsyncSession, user_id: str, file: UploadFile):
    filename = file.filename
    if not filename:
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail="Provide filename to the file")
    file_content = await file.read()
    file_obj, existing, lvr = await get_file_by_name_or_using_content(db, user_id, filename, file_content)

    # file does not exist
    if not file_obj:
        file_obj = await create_new_file(db, user_id, filename)
        lvr=0

    # version exist, avoid duplicating
    if existing:
        raise HTTPException(status.HTTP_208_ALREADY_REPORTED, detail="File is already saved")

    # save the new version
    result = await create_new_file_version(db, file_obj.id, file_content, lvr)

    return result
