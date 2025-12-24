"""
Academic Search Tool

Finds academic citations with verifiable DOIs.
Used by the Planner agent to find real sources.

Usage:
    tool = AcademicSearchTool()
    results = await tool.search("neural network optimization", max_results=5)
    for citation in results:
        print(f"{citation.authors[0]} ({citation.year}): {citation.title}")
"""

import httpx
import re
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from app.config import settings


from app.routers.generation.models import CitationMetadata


class AcademicSearchTool:
    """
    Tool for finding academic citations with verification.
    
    Uses multiple sources:
    1. CrossRef API (for DOI verification and search)
    2. Semantic Scholar API (for academic paper search)
    3. ArXiv API (for preprints)
    
    The Planner agent uses this to find real, verifiable citations
    instead of hallucinating them.
    """
    
    CROSSREF_API = "https://api.crossref.org/works"
    SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
    ARXIV_API = "http://export.arxiv.org/api/query"
    
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        source: str = "all",
    ) -> List[CitationMetadata]:
        """
        Search for academic citations.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            source: "crossref", "semantic_scholar", "arxiv", or "all"
            
        Returns:
            List of CitationMetadata objects
        """
        results = []
        
        if source in ["crossref", "all"]:
            crossref_results = await self._search_crossref(query, max_results)
            results.extend(crossref_results)
        
        if source in ["semantic_scholar", "all"]:
            ss_results = await self._search_semantic_scholar(query, max_results)
            results.extend(ss_results)
        
        # Sort by relevance and dedupe by DOI
        seen_dois = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x.relevance_score, reverse=True):
            if r.doi and r.doi in seen_dois:
                continue
            if r.doi:
                seen_dois.add(r.doi)
            unique_results.append(r)
        
        return unique_results[:max_results]
    
    async def _search_crossref(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[CitationMetadata]:
        """Search CrossRef for academic papers."""
        try:
            response = await self._client.get(
                self.CROSSREF_API,
                params={
                    "query": query,
                    "rows": max_results,
                    "select": "DOI,title,author,published-print,container-title,volume,issue,page,publisher,abstract"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            items = data.get("message", {}).get("items", [])
            
            for item in items:
                # Extract authors
                authors = []
                for author in item.get("author", []):
                    name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                    if name:
                        authors.append(name)
                
                if not authors:
                    authors = ["Unknown Author"]
                
                # Extract year
                date_parts = item.get("published-print", {}).get("date-parts", [[None]])
                year = str(date_parts[0][0]) if date_parts[0][0] else "n.d."
                
                # Extract title
                titles = item.get("title", ["Untitled"])
                title = titles[0] if titles else "Untitled"
                
                citation = CitationMetadata(
                    title=title,
                    authors=authors,
                    year=year,
                    source_type="article",
                    source_name=", ".join(item.get("container-title", [])),
                    doi=item.get("DOI"),
                    volume=item.get("volume"),
                    issue=item.get("issue"),
                    pages=item.get("page"),
                    publisher=item.get("publisher"),
                    abstract=item.get("abstract", "")[:500] if item.get("abstract") else None,
                    verified=True,  # CrossRef is authoritative
                    relevance_score=item.get("score", 0) / 100,  # Normalize score
                )
                results.append(citation)
            
            return results
            
        except Exception as e:
            print(f"CrossRef search failed: {e}")
            return []
    
    async def _search_semantic_scholar(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[CitationMetadata]:
        """Search Semantic Scholar for academic papers."""
        try:
            response = await self._client.get(
                self.SEMANTIC_SCHOLAR_API,
                params={
                    "query": query,
                    "limit": max_results,
                    "fields": "title,authors,year,venue,externalIds,abstract"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            papers = data.get("data", [])
            
            for paper in papers:
                # Extract authors
                authors = [a.get("name", "Unknown") for a in paper.get("authors", [])]
                if not authors:
                    authors = ["Unknown Author"]
                
                # Extract identifiers
                external_ids = paper.get("externalIds", {})
                doi = external_ids.get("DOI")
                arxiv_id = external_ids.get("ArXiv")
                
                citation = CitationMetadata(
                    title=paper.get("title", "Untitled"),
                    authors=authors,
                    year=str(paper.get("year", "n.d.")),
                    source_type="article",
                    source_name=paper.get("venue", ""),
                    doi=doi,
                    arxiv_id=arxiv_id,
                    url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
                    abstract=paper.get("abstract", "")[:500] if paper.get("abstract") else None,
                    verified=bool(doi),  # Verified if has DOI
                    relevance_score=0.7,  # SS doesn't provide relevance scores
                )
                results.append(citation)
            
            return results
            
        except Exception as e:
            print(f"Semantic Scholar search failed: {e}")
            return []
    
    async def verify_doi(self, doi: str) -> bool:
        """
        Verify that a DOI exists and is valid.
        
        Args:
            doi: The DOI to verify (with or without https://doi.org/ prefix)
            
        Returns:
            True if DOI is valid, False otherwise
        """
        # Clean DOI
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        
        try:
            response = await self._client.head(
                f"https://doi.org/{clean_doi}",
                follow_redirects=True
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def get_citation_by_doi(self, doi: str) -> Optional[CitationMetadata]:
        """
        Retrieve full citation metadata for a given DOI.
        
        Args:
            doi: The DOI to look up
            
        Returns:
            CitationMetadata if found, None otherwise
        """
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        
        try:
            response = await self._client.get(
                f"{self.CROSSREF_API}/{clean_doi}"
            )
            response.raise_for_status()
            data = response.json()
            
            item = data.get("message", {})
            
            # Extract authors
            authors = []
            for author in item.get("author", []):
                name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                if name:
                    authors.append(name)
            
            if not authors:
                authors = ["Unknown Author"]
            
            # Extract year
            date_parts = item.get("published-print", {}).get("date-parts", [[None]])
            year = str(date_parts[0][0]) if date_parts[0][0] else "n.d."
            
            return CitationMetadata(
                title=item.get("title", ["Untitled"])[0],
                authors=authors,
                year=year,
                source_type="article",
                source_name=", ".join(item.get("container-title", [])),
                doi=clean_doi,
                volume=item.get("volume"),
                issue=item.get("issue"),
                pages=item.get("page"),
                publisher=item.get("publisher"),
                verified=True,
                relevance_score=1.0,
            )
            
        except Exception as e:
            print(f"DOI lookup failed: {e}")
            return None
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
