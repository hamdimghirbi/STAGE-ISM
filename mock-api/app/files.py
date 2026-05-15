import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def save_upload(upload: UploadFile, user_id: int, subdir: str) -> str:
    """Validate and save an UploadFile under storage/<user_id>/<subdir>/<uuid>.<ext>.

    Returns the relative path (string) to the stored file.
    """
    if not upload.filename:
        raise HTTPException(status_code=400, detail='Empty filename')

    ext = _ext(upload.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f'Unsupported file type: {ext}')

    target_dir = settings.storage_path / str(user_id) / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f'{uuid.uuid4().hex}{ext}'
    target = target_dir / name

    size = 0
    with target.open('wb') as out:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_SIZE_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail='File too large (max 5 MB)')
            out.write(chunk)

    return str(target.relative_to(settings.storage_path.parent))
