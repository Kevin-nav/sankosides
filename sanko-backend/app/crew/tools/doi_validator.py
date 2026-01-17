"""DOI Validation Tool for Citation Auditor.

Uses the CrossRef API to validate DOIs and retrieve metadata.
"""

from crewai.tools import BaseTool
import httpx
from pydantic import Field
from typing import Any, Type
from pydantic import BaseModel


class DOIValidatorInput(BaseModel):
    """Input schema for DOI validation."""
    doi: str = Field(..., description="The DOI to validate (e.g., '10.1038/nature12373')")


class DOIValidatorTool(BaseTool):
    """Tool to validate DOIs via CrossRef API."""
    
    name: str = "validate_doi"
    description: str = """Validate a DOI and retrieve its metadata.
    Input: DOI string (e.g., "10.1038/nature12373")
    Output: Validation result with metadata if valid."""
    args_schema: Type[BaseModel] = DOIValidatorInput
    
    async def _arun(self, doi: str) -> dict:
        """Validate DOI via CrossRef API."""
        # Clean DOI
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")
        if doi.startswith("http://doi.org/"):
            doi = doi.replace("http://doi.org/", "")
        if doi.startswith("doi:"):
            doi = doi.replace("doi:", "")
        
        url = f"https://api.crossref.org/works/{doi}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    timeout=10.0,
                    headers={
                        "User-Agent": "SankoSlides/1.0 (mailto:support@sankoslides.com)"
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    message = data.get("message", {})
                    
                    # Extract year from various date fields
                    year = None
                    for date_field in ["published-print", "published-online", "issued", "created"]:
                        if date_field in message:
                            date_parts = message[date_field].get("date-parts", [[None]])
                            if date_parts and date_parts[0] and date_parts[0][0]:
                                year = date_parts[0][0]
                                break
                    
                    return {
                        "valid": True,
                        "doi": doi,
                        "title": message.get("title", [""])[0] if message.get("title") else "",
                        "authors": [
                            f"{a.get('given', '')} {a.get('family', '')}".strip()
                            for a in message.get("author", [])
                        ],
                        "year": year,
                        "journal": message.get("container-title", [""])[0] if message.get("container-title") else "",
                        "publisher": message.get("publisher", ""),
                        "type": message.get("type", ""),
                        "url": f"https://doi.org/{doi}"
                    }
                elif response.status_code == 404:
                    return {"valid": False, "doi": doi, "error": "DOI not found"}
                else:
                    return {"valid": False, "doi": doi, "error": f"HTTP {response.status_code}"}
            except httpx.TimeoutException:
                return {"valid": False, "doi": doi, "error": "Request timed out"}
            except Exception as e:
                return {"valid": False, "doi": doi, "error": str(e)}
    
    def _run(self, doi: str) -> dict:
        """Sync wrapper for DOI validation."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(doi))
                    return future.result()
            else:
                return loop.run_until_complete(self._arun(doi))
        except RuntimeError:
            # No event loop exists
            return asyncio.run(self._arun(doi))
