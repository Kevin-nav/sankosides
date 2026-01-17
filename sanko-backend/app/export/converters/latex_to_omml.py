"""
LaTeX to OMML Converter

Converts LaTeX math expressions to Office Math Markup Language (OMML)
for native, editable equations in PowerPoint.

Pipeline: LaTeX → MathML → OMML
"""

import re
from typing import Optional, Tuple
from lxml import etree
import latex2mathml.converter

from app.core.logging import get_logger

logger = get_logger(__name__)

# OMML namespace
OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
OMML_NSMAP = {None: OMML_NS}

# MathML namespace
MATHML_NS = "http://www.w3.org/1998/Math/MathML"


class LatexToOmmlConverter:
    """
    Converts LaTeX math expressions to OMML for PowerPoint.
    
    OMML (Office Math Markup Language) is the native equation format
    in Microsoft Office. Equations inserted as OMML are fully editable
    in PowerPoint, unlike embedded images.
    """
    
    def __init__(self):
        # MathML to OMML attribute mappings
        self._mathml_to_omml_tags = {
            'mrow': 'r',
            'mi': 'r',      # identifier
            'mn': 'r',      # number
            'mo': 'r',      # operator
            'mtext': 'r',   # text
            'mfrac': 'f',   # fraction
            'msqrt': 'rad', # square root
            'mroot': 'rad', # nth root
            'msup': 'sSup', # superscript
            'msub': 'sSub', # subscript
            'msubsup': 'sSubSup',
            'munder': 'limLow',
            'mover': 'limUpp',
            'munderover': 'nary',
            'mtable': 'm',  # matrix
            'mtr': 'mr',    # matrix row
            'mtd': 'e',     # matrix element
            'mfenced': 'd', # delimiters
        }
    
    def convert(self, latex: str) -> Tuple[Optional[etree._Element], Optional[str]]:
        """
        Convert LaTeX to OMML element.
        
        Args:
            latex: LaTeX math expression (without $ delimiters)
            
        Returns:
            Tuple of (OMML element, error message if failed)
        """
        try:
            # Clean up the LaTeX
            latex = self._preprocess_latex(latex)
            
            # Step 1: LaTeX → MathML
            mathml_str = latex2mathml.converter.convert(latex)
            
            # Step 2: Parse MathML
            mathml_tree = etree.fromstring(mathml_str.encode('utf-8'))
            
            # Step 3: MathML → OMML
            omml = self._mathml_to_omml(mathml_tree)
            
            logger.debug(f"Successfully converted LaTeX to OMML: {latex[:50]}...")
            return omml, None
            
        except Exception as e:
            logger.warning(f"Failed to convert LaTeX to OMML: {e}")
            return None, str(e)
    
    def _preprocess_latex(self, latex: str) -> str:
        """Clean and normalize LaTeX input."""
        # Remove surrounding $ or $$ delimiters
        latex = latex.strip()
        if latex.startswith('$$') and latex.endswith('$$'):
            latex = latex[2:-2]
        elif latex.startswith('$') and latex.endswith('$'):
            latex = latex[1:-1]
        
        # Remove \displaystyle (handled by display mode)
        latex = latex.replace(r'\displaystyle', '')
        
        return latex.strip()
    
    def _mathml_to_omml(self, mathml: etree._Element) -> etree._Element:
        """
        Convert MathML element tree to OMML.
        
        This is a simplified converter that handles common math constructs.
        For complex cases, we fall back to SVG embedding.
        """
        # Create root oMath element
        omath = etree.Element(f"{{{OMML_NS}}}oMath", nsmap=OMML_NSMAP)
        
        # Process MathML children
        self._convert_element(mathml, omath)
        
        return omath
    
    def _convert_element(self, mathml_elem: etree._Element, omml_parent: etree._Element):
        """Recursively convert MathML elements to OMML."""
        # Get local tag name (without namespace)
        tag = etree.QName(mathml_elem).localname if isinstance(mathml_elem.tag, str) else None
        
        if tag is None:
            return
        
        if tag == 'math':
            # Root element - just process children
            for child in mathml_elem:
                self._convert_element(child, omml_parent)
                
        elif tag == 'mrow':
            # Row - process children inline
            for child in mathml_elem:
                self._convert_element(child, omml_parent)
                
        elif tag in ('mi', 'mn', 'mo', 'mtext'):
            # Simple text content - create run
            self._create_run(mathml_elem.text or '', tag, omml_parent)
            
        elif tag == 'mfrac':
            # Fraction
            self._convert_fraction(mathml_elem, omml_parent)
            
        elif tag == 'msqrt':
            # Square root
            self._convert_sqrt(mathml_elem, omml_parent)
            
        elif tag == 'mroot':
            # Nth root
            self._convert_root(mathml_elem, omml_parent)
            
        elif tag == 'msup':
            # Superscript
            self._convert_superscript(mathml_elem, omml_parent)
            
        elif tag == 'msub':
            # Subscript
            self._convert_subscript(mathml_elem, omml_parent)
            
        elif tag == 'msubsup':
            # Sub-superscript
            self._convert_subsup(mathml_elem, omml_parent)
            
        elif tag in ('munder', 'mover', 'munderover'):
            # Limits/accents
            self._convert_underover(mathml_elem, omml_parent, tag)
            
        elif tag == 'mfenced':
            # Delimiters (parentheses, brackets, etc.)
            self._convert_fenced(mathml_elem, omml_parent)
            
        elif tag == 'mtable':
            # Matrix/table
            self._convert_matrix(mathml_elem, omml_parent)
            
        else:
            # Unknown element - try to process children
            for child in mathml_elem:
                self._convert_element(child, omml_parent)
    
    def _create_run(self, text: str, elem_type: str, parent: etree._Element):
        """Create an OMML run element with text."""
        r = etree.SubElement(parent, f"{{{OMML_NS}}}r")
        
        # Add run properties if needed
        if elem_type == 'mi':
            # Italic for identifiers
            rPr = etree.SubElement(r, f"{{{OMML_NS}}}rPr")
            sty = etree.SubElement(rPr, f"{{{OMML_NS}}}sty")
            sty.set(f"{{{OMML_NS}}}val", "p")  # plain (italic is default)
        
        # Add text
        t = etree.SubElement(r, f"{{{OMML_NS}}}t")
        t.text = text
    
    def _convert_fraction(self, mathml: etree._Element, parent: etree._Element):
        """Convert mfrac to OMML fraction."""
        f = etree.SubElement(parent, f"{{{OMML_NS}}}f")
        
        # Fraction properties
        fPr = etree.SubElement(f, f"{{{OMML_NS}}}fPr")
        
        children = list(mathml)
        
        # Numerator
        num = etree.SubElement(f, f"{{{OMML_NS}}}num")
        if len(children) > 0:
            self._convert_element(children[0], num)
        
        # Denominator
        den = etree.SubElement(f, f"{{{OMML_NS}}}den")
        if len(children) > 1:
            self._convert_element(children[1], den)
    
    def _convert_sqrt(self, mathml: etree._Element, parent: etree._Element):
        """Convert msqrt to OMML radical."""
        rad = etree.SubElement(parent, f"{{{OMML_NS}}}rad")
        
        # Radical properties (hide degree for sqrt)
        radPr = etree.SubElement(rad, f"{{{OMML_NS}}}radPr")
        degHide = etree.SubElement(radPr, f"{{{OMML_NS}}}degHide")
        degHide.set(f"{{{OMML_NS}}}val", "1")
        
        # Empty degree
        deg = etree.SubElement(rad, f"{{{OMML_NS}}}deg")
        
        # Content
        e = etree.SubElement(rad, f"{{{OMML_NS}}}e")
        for child in mathml:
            self._convert_element(child, e)
    
    def _convert_root(self, mathml: etree._Element, parent: etree._Element):
        """Convert mroot to OMML radical with degree."""
        rad = etree.SubElement(parent, f"{{{OMML_NS}}}rad")
        radPr = etree.SubElement(rad, f"{{{OMML_NS}}}radPr")
        
        children = list(mathml)
        
        # Degree (second child in MathML)
        deg = etree.SubElement(rad, f"{{{OMML_NS}}}deg")
        if len(children) > 1:
            self._convert_element(children[1], deg)
        
        # Content (first child in MathML)
        e = etree.SubElement(rad, f"{{{OMML_NS}}}e")
        if len(children) > 0:
            self._convert_element(children[0], e)
    
    def _convert_superscript(self, mathml: etree._Element, parent: etree._Element):
        """Convert msup to OMML superscript."""
        sSup = etree.SubElement(parent, f"{{{OMML_NS}}}sSup")
        sSupPr = etree.SubElement(sSup, f"{{{OMML_NS}}}sSupPr")
        
        children = list(mathml)
        
        # Base
        e = etree.SubElement(sSup, f"{{{OMML_NS}}}e")
        if len(children) > 0:
            self._convert_element(children[0], e)
        
        # Superscript
        sup = etree.SubElement(sSup, f"{{{OMML_NS}}}sup")
        if len(children) > 1:
            self._convert_element(children[1], sup)
    
    def _convert_subscript(self, mathml: etree._Element, parent: etree._Element):
        """Convert msub to OMML subscript."""
        sSub = etree.SubElement(parent, f"{{{OMML_NS}}}sSub")
        sSubPr = etree.SubElement(sSub, f"{{{OMML_NS}}}sSubPr")
        
        children = list(mathml)
        
        # Base
        e = etree.SubElement(sSub, f"{{{OMML_NS}}}e")
        if len(children) > 0:
            self._convert_element(children[0], e)
        
        # Subscript
        sub = etree.SubElement(sSub, f"{{{OMML_NS}}}sub")
        if len(children) > 1:
            self._convert_element(children[1], sub)
    
    def _convert_subsup(self, mathml: etree._Element, parent: etree._Element):
        """Convert msubsup to OMML sub-superscript."""
        sSubSup = etree.SubElement(parent, f"{{{OMML_NS}}}sSubSup")
        sSubSupPr = etree.SubElement(sSubSup, f"{{{OMML_NS}}}sSubSupPr")
        
        children = list(mathml)
        
        # Base
        e = etree.SubElement(sSubSup, f"{{{OMML_NS}}}e")
        if len(children) > 0:
            self._convert_element(children[0], e)
        
        # Subscript
        sub = etree.SubElement(sSubSup, f"{{{OMML_NS}}}sub")
        if len(children) > 1:
            self._convert_element(children[1], sub)
        
        # Superscript
        sup = etree.SubElement(sSubSup, f"{{{OMML_NS}}}sup")
        if len(children) > 2:
            self._convert_element(children[2], sup)
    
    def _convert_underover(self, mathml: etree._Element, parent: etree._Element, tag: str):
        """Convert munder/mover/munderover to OMML limits."""
        children = list(mathml)
        
        if tag == 'munder':
            limLow = etree.SubElement(parent, f"{{{OMML_NS}}}limLow")
            limLowPr = etree.SubElement(limLow, f"{{{OMML_NS}}}limLowPr")
            
            e = etree.SubElement(limLow, f"{{{OMML_NS}}}e")
            if len(children) > 0:
                self._convert_element(children[0], e)
            
            lim = etree.SubElement(limLow, f"{{{OMML_NS}}}lim")
            if len(children) > 1:
                self._convert_element(children[1], lim)
                
        elif tag == 'mover':
            limUpp = etree.SubElement(parent, f"{{{OMML_NS}}}limUpp")
            limUppPr = etree.SubElement(limUpp, f"{{{OMML_NS}}}limUppPr")
            
            e = etree.SubElement(limUpp, f"{{{OMML_NS}}}e")
            if len(children) > 0:
                self._convert_element(children[0], e)
            
            lim = etree.SubElement(limUpp, f"{{{OMML_NS}}}lim")
            if len(children) > 1:
                self._convert_element(children[1], lim)
                
        elif tag == 'munderover':
            # Use nary for sum/integral with limits
            nary = etree.SubElement(parent, f"{{{OMML_NS}}}nary")
            naryPr = etree.SubElement(nary, f"{{{OMML_NS}}}naryPr")
            
            # Subscript (lower limit)
            sub = etree.SubElement(nary, f"{{{OMML_NS}}}sub")
            if len(children) > 1:
                self._convert_element(children[1], sub)
            
            # Superscript (upper limit)
            sup = etree.SubElement(nary, f"{{{OMML_NS}}}sup")
            if len(children) > 2:
                self._convert_element(children[2], sup)
            
            # Element (the operator like sum/integral)
            e = etree.SubElement(nary, f"{{{OMML_NS}}}e")
            if len(children) > 0:
                self._convert_element(children[0], e)
    
    def _convert_fenced(self, mathml: etree._Element, parent: etree._Element):
        """Convert mfenced to OMML delimiters."""
        d = etree.SubElement(parent, f"{{{OMML_NS}}}d")
        dPr = etree.SubElement(d, f"{{{OMML_NS}}}dPr")
        
        # Get delimiter characters
        open_char = mathml.get('open', '(')
        close_char = mathml.get('close', ')')
        
        begChr = etree.SubElement(dPr, f"{{{OMML_NS}}}begChr")
        begChr.set(f"{{{OMML_NS}}}val", open_char)
        
        endChr = etree.SubElement(dPr, f"{{{OMML_NS}}}endChr")
        endChr.set(f"{{{OMML_NS}}}val", close_char)
        
        # Content
        e = etree.SubElement(d, f"{{{OMML_NS}}}e")
        for child in mathml:
            self._convert_element(child, e)
    
    def _convert_matrix(self, mathml: etree._Element, parent: etree._Element):
        """Convert mtable to OMML matrix."""
        m = etree.SubElement(parent, f"{{{OMML_NS}}}m")
        mPr = etree.SubElement(m, f"{{{OMML_NS}}}mPr")
        
        for row in mathml:
            if etree.QName(row).localname == 'mtr':
                mr = etree.SubElement(m, f"{{{OMML_NS}}}mr")
                for cell in row:
                    if etree.QName(cell).localname == 'mtd':
                        e = etree.SubElement(mr, f"{{{OMML_NS}}}e")
                        for child in cell:
                            self._convert_element(child, e)


# Singleton instance
_converter = None


def get_converter() -> LatexToOmmlConverter:
    """Get the singleton converter instance."""
    global _converter
    if _converter is None:
        _converter = LatexToOmmlConverter()
    return _converter


def latex_to_omml(latex: str) -> Tuple[Optional[etree._Element], Optional[str]]:
    """
    Convert LaTeX to OMML.
    
    Args:
        latex: LaTeX math expression
        
    Returns:
        Tuple of (OMML element, error message if failed)
    """
    return get_converter().convert(latex)
