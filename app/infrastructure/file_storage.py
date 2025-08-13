# infrastructure/file_storage.py

from pathlib import Path
import aiofiles

BASE_UPLOAD_DIR = Path("uploads")
BASE_UPLOAD_DIR.mkdir(exist_ok=True)

async def save_file_locally(file_id: str, version_id: str, content: bytes, original_filename: str)->str:
    """
    Save file locally in structure:
    uploads/{file_id}/{version_id}.ext

    Returns: absolute path as string
    """
    file_folder = BASE_UPLOAD_DIR / str(file_id)
    file_folder.mkdir(exist_ok=True)

    extension = Path(original_filename).suffix
    version_filename = f"{version_id}{extension}"
    file_path = file_folder / version_filename

    # with open(file_path, "wb") as buffer:
    #         buffer.write(content)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    return str(file_path.resolve())

async def fetch_local_file(file_path: str):
    """
    return the Path to the version file if it exists.
    """
    version_file_path = Path(file_path)

    if version_file_path.exists() and version_file_path.is_file():
        return version_file_path

    return None
