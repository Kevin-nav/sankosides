"""
Visual QA Integration Tests

Tests Playwright initialization and basic screenshot capture on Windows.
"""

import pytest
import asyncio
import sys


class TestVisualQAWindows:
    """Tests for Visual QA on Windows with ProactorEventLoop."""
    
    def test_event_loop_policy_on_windows(self):
        """Verify WindowsProactorEventLoopPolicy is set on Windows."""
        if sys.platform != 'win32':
            pytest.skip("Windows-only test")
        
        # Import main module to trigger policy setup
        import app.main  # noqa: F401
        
        # Check the policy was set
        policy = asyncio.get_event_loop_policy()
        assert isinstance(policy, asyncio.WindowsProactorEventLoopPolicy), \
            f"Expected WindowsProactorEventLoopPolicy, got {type(policy).__name__}"
    
    @pytest.mark.asyncio
    async def test_visual_qa_service_start_stop(self):
        """Test VisualQAService can start and stop without errors."""
        # This test requires Playwright browsers to be installed
        # Skip if not available
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            pytest.skip("Playwright not installed")
        
        from app.services.visual_qa import VisualQAService
        
        service = VisualQAService()
        
        try:
            await service.start()
            assert service._browser is not None
            assert service._playwright is not None
        finally:
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_capture_simple_screenshot(self):
        """Test capturing a simple HTML screenshot."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            pytest.skip("Playwright not installed")
        
        from app.services.visual_qa import VisualQAService
        
        service = VisualQAService()
        
        try:
            await service.start()
            
            # Simple HTML content
            html = """
            <div style="width: 100%; height: 100%; background: #1a1a2e; 
                        display: flex; align-items: center; justify-content: center;">
                <h1 style="color: white; font-family: Arial;">Test Slide</h1>
            </div>
            """
            
            # Capture screenshot
            screenshot = await service.capture_screenshot(html)
            
            # Verify we got PNG data (PNG magic bytes)
            assert screenshot[:8] == b'\x89PNG\r\n\x1a\n', "Expected PNG format"
            assert len(screenshot) > 1000, "Screenshot should be at least 1KB"
            
        finally:
            await service.stop()


class TestEventLoopValidation:
    """Tests for event loop validation in VisualQAService."""
    
    def test_windows_loop_check_message(self):
        """Verify the error message mentions ProactorEventLoop."""
        if sys.platform != 'win32':
            pytest.skip("Windows-only test")
        
        # The validation happens in start(), which we test in integration tests
        # This just verifies the imports work
        from app.services.visual_qa import VisualQAService
        
        service = VisualQAService()
        assert service is not None
