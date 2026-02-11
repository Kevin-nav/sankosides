"""
Academic Search Tool

Finds academic citations with verifiable DOIs.
Used by the Planner agent to find real sources.

Providers (in priority order):
1. CrossRef - No auth required, authoritative DOI source
2. OpenAlex - No auth required, 250M+ works, excellent coverage
3. Semantic Scholar - API key recommended for reliability

Features:
- 2-tier cache (Redis + PostgreSQL) for fast lookups
- Automatic retry with exponential backoff
- Graceful fallback between providers
- Deduplication by DOI

Usage:
    tool = AcademicSearchTool()
    results = await tool.search("neural network optimization", max_results=5)
    for citation in results:
        print(f"{citation.authors[0]} ({citation.year}): {citation.title}")
"""

import httpx
from typing import Optional, List
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import CitationMetadata
from app.services.citation_cache import CitationCacheService

logger = get_logger(__name__)

# Retry configuration for API calls
RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=1, max=10),
    "retry": retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    "before_sleep": before_sleep_log(logger, "WARNING"),
    "reraise": True,
}


class AcademicSearchTool:
    """
    Tool for finding academic citations with verification.
    
    Uses multiple sources with automatic fallback:
    1. CrossRef API (authoritative DOI source, no auth)
    2. OpenAlex API (250M+ works, no auth, excellent coverage)
    3. Semantic Scholar API (requires API key for reliability)
    
    The Planner agent uses this to find real, verifiable citations
    instead of hallucinating them.
    """
    
    CROSSREF_API = "https://api.crossref.org/works"
    OPENALEX_API = "https://api.openalex.org/works"
    SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    def __init__(self, semantic_scholar_api_key: Optional[str] = None):
        """
        Initialize the academic search tool.
        
        Args:
            semantic_scholar_api_key: Optional API key for Semantic Scholar.
                                     If not provided, will try settings.semantic_scholar_api_key
        """
        self._client = httpx.AsyncClient(timeout=30.0)
        self._ss_api_key = semantic_scholar_api_key or getattr(settings, 'semantic_scholar_api_key', None)
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        source: str = "all",
        use_cache: bool = True,
    ) -> List[CitationMetadata]:
        """
        Search for academic citations across multiple providers.
        
        Uses 2-tier cache (Redis + PostgreSQL) to minimize API calls.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            source: "crossref", "openalex", "semantic_scholar", or "all"
            use_cache: Whether to check cache first (default True)
            
        Returns:
            List of CitationMetadata objects, deduplicated by DOI
        """
        # Check Redis cache first
        if use_cache:
            cached = await CitationCacheService.get_from_redis(query)
            if cached:
                logger.info(f"Cache hit for '{query}': {len(cached)} results")
                return cached[:max_results]
            # L2 miss -> check durable cache tier
            cached_convex = await CitationCacheService.get_from_convex(query)
            if cached_convex:
                logger.info(f"Persistent cache hit for '{query}': {len(cached_convex)} results")
                return cached_convex[:max_results]
        
        results = []
        providers_used = []
        
        # CrossRef - primary, always reliable
        if source in ["crossref", "all"]:
            if await CitationCacheService.should_rate_limit("crossref"):
                logger.debug("Skipping CrossRef: provider is temporarily rate-limited")
            else:
                crossref_results = await self._search_crossref(query, max_results)
                results.extend(crossref_results)
                providers_used.append("crossref")
                logger.debug(f"CrossRef returned {len(crossref_results)} results for '{query}'")
        
        # OpenAlex - excellent coverage, no auth needed
        if source in ["openalex", "all"]:
            if await CitationCacheService.should_rate_limit("openalex"):
                logger.debug("Skipping OpenAlex: provider is temporarily rate-limited")
            else:
                openalex_results = await self._search_openalex(query, max_results)
                results.extend(openalex_results)
                providers_used.append("openalex")
                logger.debug(f"OpenAlex returned {len(openalex_results)} results for '{query}'")
        
        # Semantic Scholar - only if we have API key or explicitly requested
        if source in ["semantic_scholar", "all"]:
            # Skip if no API key and using "all" (prevents 429 errors)
            if source == "all" and not self._ss_api_key:
                logger.debug("Skipping Semantic Scholar (no API key configured)")
            else:
                if await CitationCacheService.should_rate_limit("semantic_scholar"):
                    logger.debug("Skipping Semantic Scholar: provider is temporarily rate-limited")
                else:
                    ss_results = await self._search_semantic_scholar(query, max_results)
                    results.extend(ss_results)
                    providers_used.append("semantic_scholar")
                    logger.debug(f"Semantic Scholar returned {len(ss_results)} results for '{query}'")
        
        # Sort by relevance and dedupe by DOI
        seen_dois = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x.relevance_score, reverse=True):
            if r.doi and r.doi in seen_dois:
                continue
            if r.doi:
                seen_dois.add(r.doi)
            unique_results.append(r)
        
        final_results = unique_results[:max_results]
        
        # Store in cache (async, non-blocking)
        if use_cache and final_results:
            await CitationCacheService.store_in_redis(query, final_results)
            # Best effort durable cache write to reduce cold misses across restarts
            provider_for_cache = providers_used[0] if providers_used else source
            await CitationCacheService.store_in_convex(query, final_results, provider_for_cache)
        
        logger.info(f"Academic search for '{query}': {len(final_results)} unique results from {providers_used}")
        return final_results
    
    @retry(**RETRY_CONFIG)
    async def _search_crossref(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[CitationMetadata]:
        """Search CrossRef for academic papers (no auth required)."""
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
            
        except (httpx.TimeoutException, httpx.ConnectError):
            # Let tenacity handle retries
            raise
        except Exception as e:
            logger.warning(f"CrossRef search failed: {e}")
            return []
    
    @retry(**RETRY_CONFIG)
    async def _search_openalex(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[CitationMetadata]:
        """
        Search OpenAlex for academic papers.
        
        OpenAlex is free, no auth required, covers 250M+ works.
        Adding mailto parameter gets you into the "polite pool" for faster responses.
        """
        try:
            response = await self._client.get(
                self.OPENALEX_API,
                params={
                    "search": query,
                    "per-page": max_results,
                    "mailto": "api@sankoslides.com",  # Polite pool
                    "select": "id,doi,title,authorships,publication_year,primary_location,abstract_inverted_index",
                }
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            works = data.get("results", [])
            
            for work in works:
                # Extract authors from authorships
                authors = []
                for authorship in work.get("authorships", []):
                    author_info = authorship.get("author", {})
                    name = author_info.get("display_name", "")
                    if name:
                        authors.append(name)
                
                if not authors:
                    authors = ["Unknown Author"]
                
                # Extract DOI (remove prefix if present)
                doi_url = work.get("doi", "")
                doi = doi_url.replace("https://doi.org/", "") if doi_url else None
                
                # Extract venue/journal
                primary_loc = work.get("primary_location", {}) or {}
                source = primary_loc.get("source", {}) or {}
                venue = source.get("display_name", "")
                
                # Reconstruct abstract from inverted index (OpenAlex format)
                abstract = None
                abstract_index = work.get("abstract_inverted_index")
                if abstract_index:
                    abstract = self._reconstruct_abstract(abstract_index)
                
                citation = CitationMetadata(
                    title=work.get("title", "Untitled") or "Untitled",
                    authors=authors,
                    year=str(work.get("publication_year", "n.d.")),
                    source_type="article",
                    source_name=venue,
                    doi=doi,
                    url=work.get("id"),  # OpenAlex work URL
                    abstract=abstract[:500] if abstract else None,
                    verified=bool(doi),  # Verified if has DOI
                    relevance_score=0.8,  # OpenAlex has good relevance
                )
                results.append(citation)
            
            return results
            
        except (httpx.TimeoutException, httpx.ConnectError):
            # Let tenacity handle retries
            raise
        except Exception as e:
            logger.warning(f"OpenAlex search failed: {e}")
            return []
    
    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        """Reconstruct abstract from OpenAlex inverted index format."""
        if not inverted_index:
            return ""
        
        try:
            # Build word -> positions mapping
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position and join
            word_positions.sort(key=lambda x: x[0])
            return " ".join(word for _, word in word_positions)
        except Exception:
            return ""
    
    @retry(**RETRY_CONFIG)
    
    async def _search_semantic_scholar(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[CitationMetadata]:
        """
        Search Semantic Scholar for academic papers.
        
        Note: Requires API key for reliable access. Without key, subject to
        shared public rate limits which can result in 429 errors.
        """
        try:
            headers = {}
            if self._ss_api_key:
                headers["x-api-key"] = self._ss_api_key
            
            response = await self._client.get(
                self.SEMANTIC_SCHOLAR_API,
                params={
                    "query": query,
                    "limit": max_results,
                    "fields": "title,authors,year,venue,externalIds,abstract"
                },
                headers=headers,
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
            
        except (httpx.TimeoutException, httpx.ConnectError):
            # Let tenacity handle retries
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Semantic Scholar rate limited (429). Consider adding API key.")
            else:
                logger.warning(f"Semantic Scholar search failed: {e}")
            return []
        except Exception as e:
            logger.warning(f"Semantic Scholar search failed: {e}")
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
            logger.warning(f"DOI lookup failed: {e}")
            return None
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
