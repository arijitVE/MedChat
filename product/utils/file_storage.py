import hashlib
from pathlib import Path

from fastapi import HTTPException
from shared.config import get_settings
from shared.logger import get_logger


logger = get_logger(__name__)


def _base_storage_path() -> Path:
    return Path(get_settings().STORAGE_PATH)


def get_file_path(
    patient_id: str,
    report_id: str,
    upload_count: int,
    filename: str,
) -> Path:
    return _base_storage_path() / patient_id / report_id / f"v{upload_count}" / filename


def save_file(
    patient_id: str,
    report_id: str,
    upload_count: int,
    filename: str,
    file_bytes: bytes,
) -> str:
    path = get_file_path(patient_id, report_id, upload_count, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(file_bytes)
    return str(path)


def delete_file(file_path: str) -> None:
    path = Path(file_path)
    if not path.exists():
        logger.warning("file_delete_missing", file_path=file_path)
        return
    path.unlink()


def get_file_bytes(file_path: str) -> bytes:
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return path.read_bytes()


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()
