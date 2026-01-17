"""Tests for citation utilities."""

import pytest
from app.services.citation_utils import (
    extract_inline_citations,
    find_matching_citation,
    remove_inline_citation,
    extract_all_citations_from_slides,
    sort_citations,
    AUTHOR_YEAR_PATTERN,
    MULTIPLE_CITATION_PATTERN,
    NUMBERED_PATTERN,
)
from app.models.schemas import CitationMetadata, RefinedSlide, SlideContentType


class TestExtractInlineCitations:
    """Tests for extract_inline_citations function."""
    
    def test_single_author_year(self):
        """Test extraction of single author-year citation."""
        text = "This is supported by research (Smith, 2024)."
        results = extract_inline_citations(text, "author_year")
        
        assert len(results) == 1
        author, year, start, end = results[0]
        assert author == "Smith"
        assert year == "2024"
    
    def test_two_authors(self):
        """Test extraction of two-author citation."""
        text = "According to (Jones and Brown, 2023), the results are significant."
        results = extract_inline_citations(text, "author_year")
        
        assert len(results) == 1
        author, year, _, _ = results[0]
        assert "Jones" in author
        assert "Brown" in author
        assert year == "2023"
    
    def test_et_al_citation(self):
        """Test extraction of et al. citation."""
        text = "This was confirmed by (Lee et al., 2022)."
        results = extract_inline_citations(text, "author_year")
        
        assert len(results) == 1
        author, year, _, _ = results[0]
        assert "Lee" in author
        assert "et al." in author
        assert year == "2022"
    
    def test_multiple_citations(self):
        """Test extraction of multiple citations in parentheses."""
        text = "Several studies support this (Smith, 2024; Jones, 2023)."
        results = extract_inline_citations(text, "author_year")
        
        assert len(results) >= 2
        authors = [r[0] for r in results]
        years = [r[1] for r in results]
        assert "Smith" in authors
        assert "Jones" in authors
        assert "2024" in years
        assert "2023" in years
    
    def test_numbered_format(self):
        """Test extraction of numbered citations."""
        text = "This is supported by research [1] and confirmed [2]."
        results = extract_inline_citations(text, "numbered")
        
        assert len(results) == 2
        numbers = [r[1] for r in results]
        assert "1" in numbers
        assert "2" in numbers
    
    def test_year_with_suffix(self):
        """Test extraction of year with suffix (2024a)."""
        text = "As noted by (Amegbey, 1990a)."
        results = extract_inline_citations(text, "author_year")
        
        assert len(results) == 1
        author, year, _, _ = results[0]
        assert author == "Amegbey"
        assert year == "1990a"
    
    def test_no_citations(self):
        """Test text without citations."""
        text = "This is just regular text without any citations."
        results = extract_inline_citations(text, "author_year")
        
        assert len(results) == 0


class TestFindMatchingCitation:
    """Tests for find_matching_citation function."""
    
    def test_exact_match(self):
        """Test finding exact author and year match."""
        citations = [
            CitationMetadata(title="Test Paper", authors=["John Smith"], year="2024"),
            CitationMetadata(title="Other Paper", authors=["Jane Doe"], year="2023"),
        ]
        
        result = find_matching_citation("Smith", "2024", citations)
        
        assert result is not None
        assert result.title == "Test Paper"
    
    def test_surname_match(self):
        """Test matching by surname only."""
        citations = [
            CitationMetadata(title="Test Paper", authors=["John Michael Smith"], year="2024"),
        ]
        
        result = find_matching_citation("Smith", "2024", citations)
        
        assert result is not None
        assert result.title == "Test Paper"
    
    def test_year_suffix_match(self):
        """Test matching year with suffix."""
        citations = [
            CitationMetadata(title="Test Paper", authors=["Smith"], year="2024"),
        ]
        
        result = find_matching_citation("Smith", "2024a", citations)
        
        assert result is not None
    
    def test_no_match(self):
        """Test when no match is found."""
        citations = [
            CitationMetadata(title="Test Paper", authors=["Smith"], year="2024"),
        ]
        
        result = find_matching_citation("Jones", "2023", citations)
        
        assert result is None
    
    def test_et_al_match(self):
        """Test matching et al. citation."""
        citations = [
            CitationMetadata(
                title="Test Paper", 
                authors=["John Lee", "Jane Smith", "Bob Brown"], 
                year="2022"
            ),
        ]
        
        result = find_matching_citation("Lee et al.", "2022", citations)
        
        assert result is not None


class TestRemoveInlineCitation:
    """Tests for remove_inline_citation function."""
    
    def test_remove_middle_citation(self):
        """Test removing citation from middle of text."""
        text = "This statement (Smith, 2024) is important."
        # Positions for "(Smith, 2024)"
        start = 15
        end = 29
        
        result = remove_inline_citation(text, start, end)
        
        assert "(Smith, 2024)" not in result
        assert "This statement" in result
        assert "is important" in result
    
    def test_remove_end_citation(self):
        """Test removing citation from end of text."""
        text = "This is important (Smith, 2024)"
        start = 18
        end = 32
        
        result = remove_inline_citation(text, start, end)
        
        assert "(Smith, 2024)" not in result
        assert "This is important" in result


class TestExtractAllCitationsFromSlides:
    """Tests for extract_all_citations_from_slides function."""
    
    def test_extract_unique_citations(self):
        """Test extracting unique citations from slides."""
        slides = [
            RefinedSlide(
                order=1,
                title="Slide 1",
                content_type=SlideContentType.CONTENT,
                citations=[
                    CitationMetadata(title="Paper 1", authors=["Smith"], year="2024", doi="10.1234/a"),
                    CitationMetadata(title="Paper 2", authors=["Jones"], year="2023"),
                ]
            ),
            RefinedSlide(
                order=2,
                title="Slide 2",
                content_type=SlideContentType.CONTENT,
                citations=[
                    CitationMetadata(title="Paper 1", authors=["Smith"], year="2024", doi="10.1234/a"),  # Duplicate
                    CitationMetadata(title="Paper 3", authors=["Brown"], year="2022"),
                ]
            ),
        ]
        
        result = extract_all_citations_from_slides(slides)
        
        # Should deduplicate Paper 1
        assert len(result) == 3
        titles = [c.title for c in result]
        assert "Paper 1" in titles
        assert "Paper 2" in titles
        assert "Paper 3" in titles


class TestSortCitations:
    """Tests for sort_citations function."""
    
    def test_alphabetical_sort(self):
        """Test alphabetical sorting by author surname."""
        citations = [
            CitationMetadata(title="A Paper", authors=["Zebra Smith"], year="2024"),
            CitationMetadata(title="B Paper", authors=["Aaron Jones"], year="2023"),
            CitationMetadata(title="C Paper", authors=["Mike Brown"], year="2022"),
        ]
        
        result = sort_citations(citations, "alphabetical")
        
        assert result[0].authors[0] == "Mike Brown"  # Brown comes first
        assert result[1].authors[0] == "Aaron Jones"  # Jones second
        assert result[2].authors[0] == "Zebra Smith"  # Smith last
    
    def test_appearance_sort(self):
        """Test appearance-based sorting (unchanged order)."""
        citations = [
            CitationMetadata(title="First", authors=["Zebra"], year="2024"),
            CitationMetadata(title="Second", authors=["Aaron"], year="2023"),
        ]
        
        result = sort_citations(citations, "appearance")
        
        assert result[0].title == "First"
        assert result[1].title == "Second"
