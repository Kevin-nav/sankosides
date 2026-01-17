"""
Export Storage Utilities

Handles R2 storage for exported presentations with signed URLs.
"""

import uuid
from datetime import datetime, timedelta
from typing import Tuple

from app.services.storage import get_storage_service
from app.export.models import ExportFormat
from app.core.logging import get_logger

logger = get_logger(__name__)

# Export file storage prefix
EXPORT_PREFIX = "exports"

# Default URL expiration (1 hour)
DEFAULT_EXPIRES_IN = 3600


async def upload_export(
    file_data: bytes,
    format: ExportFormat,
    presentation_title: str = "presentation",
    expires_in: int = DEFAULT_EXPIRES_IN,
) -> Tuple[str, str, datetime, int]:
    """
    Upload exported file to R2 and generate signed URL.
    
    Args:
        file_data: Exported file content as bytes
        format: Export format (pptx or pdf)
        presentation_title: Title for filename
        expires_in: URL expiration time in seconds
        
    Returns:
        Tuple of (download_url, filename, expires_at, file_size)
    """
    storage = get_storage_service()
    
    # Generate unique filename
    safe_title = _sanitize_title(presentation_title)
    unique_id = uuid.uuid4().hex[:8]
    extension = format.value
    filename = f"{safe_title}_{unique_id}.{extension}"
    
    # Build R2 key
    r2_key = f"{EXPORT_PREFIX}/{filename}"
    
    # Determine content type
    content_types = {
        ExportFormat.PPTX: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ExportFormat.PDF: "application/pdf",
    }
    content_type = content_types.get(format, "application/octet-stream")
    
    # Upload to R2
    async with storage._get_client() as client:
        await client.put_object(
            Bucket=storage.bucket_name,
            Key=r2_key,
            Body=file_data,
            ContentType=content_type,
            ContentDisposition=f'attachment; filename="{filename}"',
        )
    
    logger.info(f"Uploaded export to R2: {r2_key} ({len(file_data)} bytes)")
    
    # Generate signed URL
    download_url = await storage.get_presigned_url(r2_key, expires_in=expires_in)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    return download_url, filename, expires_at, len(file_data)


def _sanitize_title(title: str) -> str:
    """Sanitize presentation title for use in filename."""
    import re
    # Remove special characters, keep alphanumeric and spaces
    safe = re.sub(r'[^a-zA-Z0-9\s-]', '', title)
    # Replace spaces with underscores
    safe = re.sub(r'\s+', '_', safe.strip())
    # Limit length
    return safe[:50] if len(safe) > 50 else safe if safe else "presentation"


async def cleanup_expired_exports(older_than_hours: int = 24) -> int:
    """
    Clean up expired export files from R2.
    
    Args:
        older_than_hours: Delete exports older than this many hours
        
    Returns:
        Number of files deleted
    """
    # TODO: Implement cleanup of old exports
    # This would list objects with prefix and delete those older than threshold
    logger.info(f"Export cleanup requested (older than {older_than_hours}h)")
    return 0
