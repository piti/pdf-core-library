"""
Input processing module for PDF Core Library.

Handles markdown file parsing, frontmatter extraction, and content preprocessing.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

import frontmatter
import markdown
from markdown.extensions import tables, fenced_code, codehilite, toc, footnotes

from .content_types import ProcessedInput

logger = logging.getLogger(__name__)


class InputProcessor:
    """
    Processes markdown files with frontmatter for PDF generation.
    
    Features:
    - YAML frontmatter parsing
    - GitHub-flavored markdown support
    - Custom shortcode processing
    - Content validation and preprocessing
    """
    
    def __init__(self, markdown_extensions: Optional[List[str]] = None):
        """
        Initialize the InputProcessor.
        
        Args:
            markdown_extensions: List of markdown extensions to enable
        """
        self.markdown_extensions = markdown_extensions or [
            'tables',
            'fenced_code',
            'codehilite',
            'toc',
            'footnotes',
            'attr_list',
            'def_list',
            'abbr'
        ]
        
        self.md = markdown.Markdown(
            extensions=self.markdown_extensions,
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': True
                },
                'toc': {
                    'permalink': True,
                    'baselevel': 1
                }
            }
        )
        
    def process_file(self, file_path: Path) -> ProcessedInput:
        """
        Process a markdown file and return structured data.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            ProcessedInput: Structured document data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file content is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            content = file_path.read_text(encoding='utf-8')
            return self.process_content(content, str(file_path))
        except Exception as e:
            raise ValueError(f"Error processing file {file_path}: {e}")
    
    def process_content(self, content: str, filename: str = "content.md") -> ProcessedInput:
        """
        Process markdown content directly from string.
        
        Args:
            content: Markdown content with optional frontmatter
            filename: Filename for reference
            
        Returns:
            ProcessedInput: Structured document data
        """
        try:
            # Parse frontmatter and content
            post = frontmatter.loads(content)
            metadata = post.metadata
            raw_markdown = post.content
            
            # Process shortcodes before markdown conversion
            processed_content = self._process_shortcodes(raw_markdown)
            
            # Convert markdown to HTML
            html_content = self.md.convert(processed_content)
            
            # Reset markdown processor for next use
            self.md.reset()
            
            # Calculate word count
            word_count = self._calculate_word_count(raw_markdown)
            
            # Extract standard metadata
            title = metadata.get('title', self._extract_title_from_content(raw_markdown))
            author = metadata.get('author', '')
            date = metadata.get('date', '')
            
            return ProcessedInput(
                title=title,
                author=author,
                date=date,
                metadata=metadata,
                html_content=html_content,
                word_count=word_count
            )
            
        except Exception as e:
            logger.error(f"Error processing content from {filename}: {e}")
            raise ValueError(f"Error processing markdown content: {e}")
    
    def _process_shortcodes(self, content: str) -> str:
        """
        Process custom shortcodes in content.
        
        Args:
            content: Raw markdown content
            
        Returns:
            Content with shortcodes processed
        """
        # Process TOC shortcode
        content = re.sub(r'\[TOC\]', '', content, flags=re.IGNORECASE)
        
        # Process break shortcodes
        content = re.sub(r'\[BREAK\]', '<div class="page-break"></div>', content, flags=re.IGNORECASE)
        content = re.sub(r'\[PAGE_BREAK\]', '<div class="page-break"></div>', content, flags=re.IGNORECASE)
        
        # Process info boxes
        content = re.sub(
            r'\[INFO\](.*?)\[/INFO\]', 
            r'<div class="info-box">\1</div>', 
            content, 
            flags=re.IGNORECASE | re.DOTALL
        )
        
        content = re.sub(
            r'\[WARNING\](.*?)\[/WARNING\]', 
            r'<div class="warning-box">\1</div>', 
            content, 
            flags=re.IGNORECASE | re.DOTALL
        )
        
        content = re.sub(
            r'\[SUCCESS\](.*?)\[/SUCCESS\]', 
            r'<div class="success-box">\1</div>', 
            content, 
            flags=re.IGNORECASE | re.DOTALL
        )
        
        return content
    
    def _extract_title_from_content(self, content: str) -> str:
        """
        Extract title from markdown content if not in frontmatter.
        
        Args:
            content: Raw markdown content
            
        Returns:
            Extracted title or empty string
        """
        # Look for first H1 heading
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # Look for underlined heading
        lines = content.split('\n')
        for i, line in enumerate(lines[:-1]):
            if line.strip() and lines[i + 1].strip().startswith('='):
                return line.strip()
        
        return ""
    
    def _calculate_word_count(self, content: str) -> int:
        """
        Calculate word count of text content.
        
        Args:
            content: Raw text content
            
        Returns:
            Word count
        """
        # Remove markdown formatting
        text = re.sub(r'[#*_`\[\]()]', '', content)
        
        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`.*?`', '', text)
        
        # Remove links
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)
        
        # Count words
        words = text.split()
        return len([word for word in words if word.strip()])