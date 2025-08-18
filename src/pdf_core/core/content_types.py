"""
Content type definitions for PDF core library.

This module provides the basic data structures needed for template rendering
without dependencies on specific input processors.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class ProcessedInput:
    """
    Represents processed input content ready for template rendering.
    
    This is a minimal interface that can be implemented by various
    input processors (markdown, HTML, etc.) in the tools/SaaS layers.
    """
    
    title: str = ""
    author: str = ""
    date: str = ""
    html_content: str = ""
    word_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure metadata is not None
        if self.metadata is None:
            self.metadata = {}
            
        if not self.date and self.metadata.get("auto_date", True):
            self.date = datetime.now().strftime("%Y-%m-%d")
            
        if not self.word_count and self.html_content:
            # Simple word count estimation from HTML content
            import re
            text_content = re.sub(r'<[^>]+>', '', self.html_content)
            self.word_count = len(text_content.split())


@dataclass 
class RenderedTemplate:
    """Represents a fully rendered template ready for PDF generation."""
    
    html_content: str
    css_embedded: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    template_name: str = ""
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PDFOutput:
    """Represents the final PDF output."""
    
    pdf_bytes: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_size: int = 0
    generation_time: float = 0.0
    
    def __post_init__(self):
        """Post-initialization processing.""" 
        if self.metadata is None:
            self.metadata = {}
            
        if not self.file_size and self.pdf_bytes:
            self.file_size = len(self.pdf_bytes)