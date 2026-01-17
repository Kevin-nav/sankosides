"""
Tests for the PDF upload integration.

Tests the /upload endpoint, cache checking, and file hash handling.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from io import BytesIO

# Test the upload endpoint with mocked storage and cache services


class TestUploadEndpoint:
    """Tests for the /api/generation/upload endpoint."""
    
    @pytest.fixture
    def mock_pdf_content(self):
        """Create mock PDF content."""
        # Simple PDF header
        return b"%PDF-1.4 fake pdf content for testing"
    
    @pytest.fixture
    def mock_upload_file(self, mock_pdf_content):
        """Create a mock UploadFile object."""
        from fastapi import UploadFile
        from io import BytesIO
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test_document.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=mock_pdf_content)
        return mock_file
    
    @pytest.mark.asyncio
    async def test_validate_upload_file_accepts_pdf(self):
        """Test that PDF files are accepted."""
        from app.api.routers.generation import validate_upload_file
        from fastapi import UploadFile
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "document.pdf"
        mock_file.content_type = "application/pdf"
        
        # Should not raise
        validate_upload_file(mock_file)
    
    @pytest.mark.asyncio
    async def test_validate_upload_file_rejects_non_pdf(self):
        """Test that non-PDF files are rejected."""
        from app.api.routers.generation import validate_upload_file
        from fastapi import UploadFile, HTTPException
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "document.txt"
        mock_file.content_type = "text/plain"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_upload_file(mock_file)
        assert exc_info.value.status_code == 400
        assert "PDF" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_file_upload_result_model(self):
        """Test the FileUploadResult model structure."""
        from app.api.routers.generation import FileUploadResult
        
        result = FileUploadResult(
            file_hash="abc123def456",
            filename="test.pdf",
            size_bytes=1024,
            r2_key="pdfs/abc123/test.pdf",
            cached=False,
            sections_count=None,
        )
        
        assert result.file_hash == "abc123def456"
        assert result.cached is False
    
    @pytest.mark.asyncio
    async def test_file_upload_result_cached_model(self):
        """Test the FileUploadResult model with cache hit."""
        from app.api.routers.generation import FileUploadResult
        
        result = FileUploadResult(
            file_hash="abc123def456",
            filename="test.pdf",
            size_bytes=1024,
            r2_key="pdfs/abc123/test.pdf",
            cached=True,
            sections_count=15,
        )
        
        assert result.cached is True
        assert result.sections_count == 15
    
    @pytest.mark.asyncio
    async def test_file_upload_response_model(self):
        """Test the FileUploadResponse model structure."""
        from app.api.routers.generation import FileUploadResponse, FileUploadResult
        
        files = [
            FileUploadResult(
                file_hash="hash1",
                filename="doc1.pdf",
                size_bytes=1024,
                r2_key="pdfs/hash1/doc1.pdf",
                cached=True,
                sections_count=10,
            ),
            FileUploadResult(
                file_hash="hash2",
                filename="doc2.pdf",
                size_bytes=2048,
                r2_key="pdfs/hash2/doc2.pdf",
                cached=False,
                sections_count=None,
            ),
        ]
        
        response = FileUploadResponse(
            files=files,
            total_cached=1,
            message="2 file(s) uploaded. 1 already cached.",
        )
        
        assert len(response.files) == 2
        assert response.total_cached == 1
        assert "cached" in response.message


class TestClarifyWithFileHashes:
    """Tests for the /clarify endpoint with file_hashes parameter."""
    
    @pytest.mark.asyncio
    async def test_clarify_request_accepts_file_hashes(self):
        """Test that ClarifyRequest accepts file_hashes."""
        from app.api.routers.generation import ClarifyRequest
        
        request = ClarifyRequest(
            message="Here's my topic",
            file_hashes=["hash1", "hash2"],
        )
        
        assert request.message == "Here's my topic"
        assert len(request.file_hashes) == 2
    
    @pytest.mark.asyncio
    async def test_clarify_request_optional_file_hashes(self):
        """Test that file_hashes is optional in ClarifyRequest."""
        from app.api.routers.generation import ClarifyRequest
        
        request = ClarifyRequest(message="Just a message")
        
        assert request.message == "Just a message"
        assert request.file_hashes is None


class TestStorageService:
    """Tests for the R2StorageService."""
    
    @pytest.mark.asyncio
    async def test_hash_computation(self):
        """Test that file hash is computed correctly."""
        from app.services.storage import R2StorageService
        
        content = b"test pdf content"
        
        hash1 = R2StorageService.calculate_hash(content)
        hash2 = R2StorageService.calculate_hash(content)
        
        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex is 64 chars
    
    @pytest.mark.asyncio
    async def test_different_content_different_hash(self):
        """Test that different content produces different hashes."""
        from app.services.storage import R2StorageService
        
        hash1 = R2StorageService.calculate_hash(b"content 1")
        hash2 = R2StorageService.calculate_hash(b"content 2")
        
        assert hash1 != hash2


class TestPDFCacheService:
    """Tests for the PDFCacheService."""
    
    @pytest.mark.asyncio
    async def test_cache_service_instantiation(self):
        """Test that PDFCacheService can be instantiated."""
        from app.services.storage import PDFCacheService
        
        service = PDFCacheService()
        assert service is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
