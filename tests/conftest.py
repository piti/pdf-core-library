"""
Shared test configuration and fixtures for pdf-core library.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import yaml

from pdf_core import BrandManager, PDFGenerator, TemplateEngine, AsyncPDFGenerator
from pdf_core.services import LocalStorage


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_brands_dir(temp_dir):
    """Create a temporary brands directory with test structure."""
    brands_dir = temp_dir / "brands"
    brands_dir.mkdir(parents=True)
    
    # Create test brand structure
    test_brand_dir = brands_dir / "test_brand"
    test_brand_dir.mkdir()
    
    # Assets directory
    assets_dir = test_brand_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "images").mkdir()
    (assets_dir / "fonts").mkdir()
    
    # Templates directory  
    templates_dir = test_brand_dir / "templates"
    templates_dir.mkdir()
    
    # Brand config
    brand_config = {
        "brand": {
            "name": "Test Brand",
            "tagline": "Testing Excellence",
            "website": "https://test.example.com"
        },
        "colors": {
            "primary": "#1E3A8A",
            "secondary": "#3B82F6", 
            "accent": "#F59E0B"
        },
        "typography": {
            "primary_font": "Inter",
            "secondary_font": "Source Sans Pro"
        },
        "assets": {
            "logo": "assets/images/logo.svg",
            "stylesheet": "assets/test_style.css"
        }
    }
    
    with open(test_brand_dir / "brand_config.yaml", "w") as f:
        yaml.dump(brand_config, f)
    
    # Create basic CSS file
    css_content = """
    .brand-primary { color: #1E3A8A; }
    .brand-secondary { color: #3B82F6; }
    .brand-accent { color: #F59E0B; }
    """
    with open(assets_dir / "test_style.css", "w") as f:
        f.write(css_content)
    
    # Create basic logo SVG
    logo_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <circle cx="50" cy="50" r="40" fill="#1E3A8A"/>
    </svg>"""
    with open(assets_dir / "images" / "logo.svg", "w") as f:
        f.write(logo_svg)
    
    # Create basic template
    template_html = """<!DOCTYPE html>
<html>
<head>
    <title>{{ title or "Test Document" }}</title>
    <style>{{ stylesheet_content }}</style>
</head>
<body>
    <header>
        <img src="{{ brand.assets.logo }}" alt="{{ brand.name }}">
        <h1>{{ title }}</h1>
    </header>
    <main>{{ html_content }}</main>
    <footer>{{ brand.name }}</footer>
</body>
</html>"""
    with open(templates_dir / "document.html", "w") as f:
        f.write(template_html)
    
    return brands_dir


@pytest.fixture
def brand_manager(test_brands_dir):
    """Create a BrandManager instance with test data."""
    return BrandManager(brands_root=test_brands_dir)


@pytest.fixture
def test_storage(temp_dir):
    """Create a test storage instance."""
    return LocalStorage(base_path=temp_dir)


@pytest.fixture
def pdf_generator():
    """Create a PDFGenerator instance for testing."""
    return PDFGenerator()


@pytest.fixture
def template_engine():
    """Create a TemplateEngine instance for testing."""
    return TemplateEngine()


@pytest.fixture
async def async_pdf_generator():
    """Create an AsyncPDFGenerator instance for testing."""
    generator = AsyncPDFGenerator()
    yield generator
    if hasattr(generator, 'browser') and generator.browser:
        await generator.browser.close()


@pytest.fixture
def sample_markdown_content():
    """Sample markdown content for testing."""
    return """---
title: "Test Document"
author: "Test Author"
template: "document"
---

# Test Document

This is a **test document** with some content.

## Features

- Professional formatting
- Brand consistency  
- High-quality output

## Conclusion

This document demonstrates the PDF generation capabilities.
"""


@pytest.fixture
def sample_brand_config():
    """Sample brand configuration for testing."""
    return {
        "brand": {
            "name": "Sample Brand",
            "tagline": "Quality Testing",
            "website": "https://sample.example.com"
        },
        "colors": {
            "primary": "#2D7D8A",
            "secondary": "#1E3A8A",
            "accent": "#F59E0B"
        },
        "typography": {
            "primary_font": "Arial",
            "secondary_font": "Georgia"
        }
    }


@pytest.fixture(autouse=True)
def cleanup_playwright():
    """Ensure Playwright resources are cleaned up after each test."""
    yield
    # Any cleanup code if needed