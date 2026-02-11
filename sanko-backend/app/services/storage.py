"""
R2 Storage Service

Async storage service for Cloudflare R2 (S3-compatible).

Features:
- Content-hash based deduplication (same file only stored once)
- KnowledgeBase caching in PostgreSQL (same file only processed once)
- Async upload/download with aioboto3
- Pre-signed URLs for temporary access
"""

import hashlib
import json
import time
from typing import Optional, Tuple, Any
from contextlib import asynccontextmanager
from datetime import datetime

import aioboto3
from botocore.config import Config
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import KnowledgeBase

logger = get_logger(__name__)


class R2StorageService:
    """
    Async storage service for Cloudflare R2.
    
    Storage Structure:
    ```
    {bucket}/
    └── uploads/
        └── {file_hash}/
            └── {sanitized_filename}.pdf
    ```
    
    Note: KnowledgeBase cache is stored in PostgreSQL, not R2.
    """
    
    def __init__(self):
        self.bucket_name = settings.r2_bucket_name
        self.account_id = settings.r2_account_id
        self.access_key_id = settings.r2_access_key_id
        self.secret_access_key = settings.r2_secret_access_key
        self.public_url = settings.r2_public_url
        
        # R2 endpoint format
        self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
        
        # boto3 configuration for retries and R2 compatibility
        # CRITICAL: R2 requires SigV4 - SigV2 causes "Unauthorized" errors
        self._boto_config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=10,
            read_timeout=30,
            signature_version='s3v4',
        )
        
        # aioboto3 session
        self._session = aioboto3.Session()
    
    def _is_configured(self) -> bool:
        """Check if R2 credentials are configured."""
        return bool(
            self.account_id
            and self.access_key_id
            and self.secret_access_key
            and self.bucket_name
        )
    
    @asynccontextmanager
    async def _get_client(self):
        """Get async S3 client for R2."""
        if not self._is_configured():
            raise RuntimeError("R2 storage not configured. Check environment variables.")
        
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=self._boto_config,
        ) as client:
            yield client
    
    @staticmethod
    def calculate_hash(data: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        import re
        # Remove path separators and dangerous characters
        safe = re.sub(r'[/\\:*?"<>|]', '_', filename)
        # Limit length
        return safe[:200] if len(safe) > 200 else safe
    
    async def upload_file(
        self,
        file_data: bytes,
        original_filename: str,
        content_type: str = "application/pdf",
    ) -> Tuple[str, str, bool]:
        """
        Upload file to R2 with content-hash deduplication.
        
        Args:
            file_data: File content as bytes
            original_filename: Original filename for reference
            content_type: MIME type of the file
            
        Returns:
            Tuple of (file_hash, r2_key, was_cached)
            - file_hash: SHA-256 hash of content
            - r2_key: Full path in R2
            - was_cached: True if file already existed (not re-uploaded)
        """
        # Calculate content hash
        file_hash = self.calculate_hash(file_data)
        safe_name = self.sanitize_filename(original_filename)
        
        # Build R2 key
        r2_key = f"uploads/{file_hash}/{safe_name}"
        
        async with self._get_client() as client:
            # Check if file already exists (deduplication)
            try:
                await client.head_object(Bucket=self.bucket_name, Key=r2_key)
                logger.info(f"File already exists in R2: {r2_key}")
                return file_hash, r2_key, True
            except Exception as e:
                # File doesn't exist, continue to upload
                if "404" not in str(e) and "NoSuchKey" not in str(e):
                    raise
            
            # Upload new file
            logger.info(f"Uploading file to R2: {r2_key}")
            await client.put_object(
                Bucket=self.bucket_name,
                Key=r2_key,
                Body=file_data,
                ContentType=content_type,
            )
            
            return file_hash, r2_key, False
    
    async def download_file(self, r2_key: str) -> bytes:
        """Download file content from R2."""
        async with self._get_client() as client:
            response = await client.get_object(Bucket=self.bucket_name, Key=r2_key)
            async with response["Body"] as stream:
                return await stream.read()
    
    async def get_presigned_url(
        self,
        r2_key: str,
        expires_in: int = 3600,
        operation: str = "get_object",
    ) -> str:
        """
        Generate a pre-signed URL for temporary access.
        
        Args:
            r2_key: Object key in R2
            expires_in: URL expiration time in seconds (default: 1 hour)
            operation: 'get_object' or 'put_object'
            
        Returns:
            Pre-signed URL string
        """
        async with self._get_client() as client:
            url = await client.generate_presigned_url(
                ClientMethod=operation,
                Params={"Bucket": self.bucket_name, "Key": r2_key},
                ExpiresIn=expires_in,
            )
            return url
    
    def get_public_url(self, r2_key: str) -> Optional[str]:
        """
        Get public URL if custom domain is configured.
        
        Returns None if no public URL is configured.
        """
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{r2_key}"
        return None
    
    async def delete_file(self, r2_key: str) -> bool:
        """Delete a file from R2."""
        async with self._get_client() as client:
            try:
                await client.delete_object(Bucket=self.bucket_name, Key=r2_key)
                return True
            except Exception as e:
                logger.error(f"Failed to delete {r2_key}: {e}")
                return False
    
    async def exists(self, r2_key: str) -> bool:
        """
        Check if a file exists in R2.
        
        Args:
            r2_key: Object key in R2
            
        Returns:
            True if file exists, False otherwise
        """
        async with self._get_client() as client:
            try:
                await client.head_object(Bucket=self.bucket_name, Key=r2_key)
                return True
            except Exception as e:
                # 404/NoSuchKey means file doesn't exist
                if "404" in str(e) or "NoSuchKey" in str(e):
                    return False
                # Other errors, log and return False
                logger.warning(f"Error checking existence of {r2_key}: {e}")
                return False


class PDFCacheService:
    """
    Service for caching PDF → KnowledgeBase mappings.
    
    2-tier cache:
    - L2: Redis (24-hour TTL) - Fast access
    - L3: PostgreSQL - Permanent storage
    
    Session-independent: same file hash = same cached result for everyone.
    """
    
    @staticmethod
    async def get_cached(
        file_hash: str,
        client: Any = None,
        db_session: Any = None,
    ) -> Optional[KnowledgeBase]:
        """
        Get cached KnowledgeBase for a file hash.
        
        Checks L2 (Redis) first, then L3 (PostgreSQL).
        If found in PostgreSQL, populates Redis for faster future access.
        
        Args:
            file_hash: SHA-256 hash of PDF content
            client: Optional cache backend client (reserved for L3 cache)
            db_session: Optional DB session (legacy compatibility)
            
        Returns:
            KnowledgeBase if cached, None otherwise
        """
        from app.services.unified_cache import pdf_kb_cache
        
        cache_key = file_hash
        
        # L2: Check Redis first (skip L1 - KB objects are too large)
        cached_dict = pdf_kb_cache.get(cache_key)
        if cached_dict:
            logger.info(f"PDF KB L2 cache HIT: {file_hash[:16]}...")
            return KnowledgeBase(**cached_dict)
        
        # L3: Check persistent cache table (feature-flagged)
        if not settings.enable_convex_cache:
            # Explicitly disabled
            logger.info(f"PDF KB L3 cache lookup DISABLED (feature flag): {file_hash[:16]}...")
            return None

        if db_session is None:
            logger.debug(f"PDF KB L3 lookup skipped (no db_session): {file_hash[:16]}...")
            return None

        try:
            result = await db_session.execute(
                text(
                    """
                    SELECT knowledge_base
                    FROM pdf_cache
                    WHERE file_hash = :file_hash
                    LIMIT 1
                    """
                ),
                {"file_hash": file_hash},
            )
            row = result.fetchone()
            if row and row[0]:
                kb_payload = row[0]
                if isinstance(kb_payload, str):
                    kb_payload = json.loads(kb_payload)

                logger.info(f"PDF KB L3 cache HIT: {file_hash[:16]}... (populating L2)")
                pdf_kb_cache.set(cache_key, kb_payload, skip_l1=True)
                return KnowledgeBase(**kb_payload)
        except Exception as e:
            logger.warning(f"PDF KB L3 cache lookup failed: {e}")
        
        logger.info(f"PDF KB cache MISS: {file_hash[:16]}...")
        return None
    
    @staticmethod
    async def save_cache(
        file_hash: str,
        r2_key: str,
        knowledge_base: KnowledgeBase,
        client: Any = None,
        db_session: Any = None,
        original_filename: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
    ) -> None:
        """
        Cache a KnowledgeBase result in PostgreSQL and Redis.
        
        Args:
            file_hash: SHA-256 hash of PDF content
            r2_key: R2 storage key for the file
            knowledge_base: Extracted KnowledgeBase
            client: Optional cache backend client (reserved for L3 cache)
            db_session: Optional DB session (legacy compatibility)
            original_filename: Original filename (optional)
            file_size_bytes: File size in bytes (optional)
            processing_time_ms: Processing time (optional)
        """
        from app.services.unified_cache import pdf_kb_cache
        
        kb_dict = knowledge_base.model_dump()
        
        # Save to L3 (persistent DB table)
        if not settings.enable_convex_cache:
            logger.info("PDF KB L3 cache save DISABLED (feature flag)")
        else:
            if db_session is None:
                logger.debug(f"PDF KB L3 save skipped (no db_session): {file_hash[:16]}...")
            else:
                try:
                    await db_session.execute(
                        text(
                            """
                            INSERT INTO pdf_cache (
                                file_hash,
                                created_at,
                                original_filename,
                                r2_key,
                                knowledge_base,
                                sections_count,
                                file_size_bytes,
                                processing_time_ms,
                                model_version
                            )
                            VALUES (
                                :file_hash,
                                :created_at,
                                :original_filename,
                                :r2_key,
                                CAST(:knowledge_base AS JSONB),
                                :sections_count,
                                :file_size_bytes,
                                :processing_time_ms,
                                :model_version
                            )
                            ON CONFLICT (file_hash)
                            DO UPDATE SET
                                created_at = EXCLUDED.created_at,
                                original_filename = EXCLUDED.original_filename,
                                r2_key = EXCLUDED.r2_key,
                                knowledge_base = EXCLUDED.knowledge_base,
                                sections_count = EXCLUDED.sections_count,
                                file_size_bytes = EXCLUDED.file_size_bytes,
                                processing_time_ms = EXCLUDED.processing_time_ms,
                                model_version = EXCLUDED.model_version
                            """
                        ),
                        {
                            "file_hash": file_hash,
                            "created_at": datetime.utcnow(),
                            "original_filename": original_filename,
                            "r2_key": r2_key,
                            "knowledge_base": json.dumps(kb_dict, default=str),
                            "sections_count": len(kb_dict.get("sections", [])),
                            "file_size_bytes": file_size_bytes,
                            "processing_time_ms": processing_time_ms,
                            "model_version": settings.model_flash,
                        },
                    )
                    await db_session.commit()
                except Exception as e:
                    await db_session.rollback()
                    logger.warning(f"PDF KB L3 cache save failed: {e}")
        
        # Also populate L2 (Redis) for faster future access
        pdf_kb_cache.set(file_hash, kb_dict, skip_l1=True)
        
        logger.info(f"Cached KnowledgeBase (L2+L3) for hash: {file_hash[:16]}...")
    
    @staticmethod
    async def exists(
        file_hash: str,
        client: Any = None,
        db_session: Any = None,
    ) -> bool:
        """Check if a file hash exists in cache."""
        if not settings.enable_convex_cache:
            logger.debug(f"PDF KB L3 cache existence check DISABLED (feature flag): {file_hash[:16]}...")
            return False

        if db_session is None:
            logger.debug(f"PDF KB L3 existence check skipped (no db_session): {file_hash[:16]}...")
            return False

        try:
            result = await db_session.execute(
                text(
                    """
                    SELECT 1
                    FROM pdf_cache
                    WHERE file_hash = :file_hash
                    LIMIT 1
                    """
                ),
                {"file_hash": file_hash},
            )
            return result.fetchone() is not None
        except Exception as e:
            logger.warning(f"PDF KB L3 cache existence check failed: {e}")
            return False


# Global singleton instances
_storage_service: Optional[R2StorageService] = None


def get_storage_service() -> R2StorageService:
    """Get or create the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = R2StorageService()
    return _storage_service


def get_cache_service() -> PDFCacheService:
    """Get PDF cache service (stateless, creates new instance)."""
    return PDFCacheService()
