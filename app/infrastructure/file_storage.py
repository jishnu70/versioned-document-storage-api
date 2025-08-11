from pathlib import Path

BASE_UPLOAD_DIR = Path("uploads")
BASE_UPLOAD_DIR.mkdir(exist_ok=True)

def save_file_locally(file_id: str, version_id: str, content: bytes, original_filename: str)->str:
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

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    return str(file_path.resolve())

def fetch_local_file(file_id: str, version: str):
    """
    Given a file ID and a version ID,
    return the Path to the version file if it exists.
    """
    folder_path = BASE_UPLOAD_DIR / str(file_id)

    if not folder_path.exists() or not folder_path.is_dir():
        return None

    version_file_path = folder_path / str(version)

    if version_file_path.exists() and version_file_path.is_file():
        return version_file_path

    return None
