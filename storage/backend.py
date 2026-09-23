import os
import logging
from abc import ABC, abstractmethod
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from shared.config import get_settings

logger = logging.getLogger(__name__)

class StorageBackend(ABC):
    @abstractmethod
    def upload_file(self, file_bytes: bytes, case_id: str, doc_id: str, filename: str) -> str:
        pass

    @abstractmethod
    def download_file(self, key: str) -> bytes:
        pass

    @abstractmethod
    def delete_file(self, key: str):
        pass

    @abstractmethod
    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        pass

class LocalStorage(StorageBackend):
    def __init__(self):
        settings = get_settings()
        self.base_dir = settings.STORAGE_PATH

    def upload_file(self, file_bytes: bytes, case_id: str, doc_id: str, filename: str) -> str:
        storage_dir = os.path.join(self.base_dir, "cases", case_id)
        os.makedirs(storage_dir, exist_ok=True)
        key = f"cases/{case_id}/{doc_id}_{filename}"
        storage_path = os.path.join(self.base_dir, key)
        
        with open(storage_path, "wb") as f:
            f.write(file_bytes)
        return key

    def download_file(self, key: str) -> bytes:
        settings = get_settings()
        storage_path = os.path.join(settings.STORAGE_PATH, key)
        with open(storage_path, "rb") as f:
            return f.read()

    def delete_file(self, key: str):
        settings = get_settings()
        storage_path = os.path.join(settings.STORAGE_PATH, key)
        if os.path.exists(storage_path):
            os.remove(storage_path)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        settings = get_settings()
        return f"file://{os.path.join(os.path.abspath(settings.STORAGE_PATH), key)}"

class MinIOStorage(StorageBackend):
    def __init__(self):
        settings = get_settings()
        self.bucket = settings.MINIO_BUCKET
        # Config: force path-style URLs (required for Supabase S3)
        # and use SigV4 signing (required for Supabase/MinIO compatibility)
        s3_config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            region_name="us-east-1",
            config=s3_config,
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception as e:
                logger.warning(
                    f"[Storage] Could not create bucket '{self.bucket}' via S3 API ({e}). "
                    "Ensure the bucket exists in your Supabase or S3 dashboard."
                )

    def upload_file(self, file_bytes: bytes, case_id: str, doc_id: str, filename: str) -> str:
        key = f"cases/{case_id}/{doc_id}_{filename}"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=file_bytes)
        return key

    def download_file(self, key: str) -> bytes:
        logger.info(f"[Storage] Downloading from bucket='{self.bucket}' key='{key}'")
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        file_bytes = response["Body"].read()

        if not file_bytes:
            raise ValueError(
                f"[Storage] Download returned empty bytes for key='{key}' in bucket='{self.bucket}'"
            )

        # Validate the downloaded bytes are a real PDF or image, not an S3 error XML body
        is_pdf = file_bytes.startswith(b"%PDF")
        is_jpeg = file_bytes[:3] == b"\xff\xd8\xff"
        is_png = file_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        is_tiff = file_bytes[:4] in (b"II*\x00", b"MM\x00*")
        if not (is_pdf or is_jpeg or is_png or is_tiff):
            preview = file_bytes[:120].decode("utf-8", errors="replace")
            raise ValueError(
                f"[Storage] Downloaded bytes for key='{key}' are not a valid PDF or image. "
                f"First 120 bytes: {preview!r}"
            )

        logger.info(f"[Storage] Downloaded {len(file_bytes)} bytes for key='{key}'")
        return file_bytes

    def delete_file(self, key: str):
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expires_in
        )

_storage_instance = None

def get_storage() -> StorageBackend:
    global _storage_instance
    if _storage_instance is None:
        settings = get_settings()
        if settings.STORAGE_BACKEND == "minio" or settings.MINIO_ENDPOINT:
            _storage_instance = MinIOStorage()
        else:
            _storage_instance = LocalStorage()
    return _storage_instance
