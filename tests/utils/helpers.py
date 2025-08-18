"""
Test helper utilities for pdf-core library.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


def create_test_brand(
    brands_root: Path,
    brand_name: str,
    config: Optional[Dict[str, Any]] = None
) -> Path:
    """
    Create a test brand directory with proper structure.
    
    Args:
        brands_root: Root directory for brands
        brand_name: Name of the brand to create
        config: Optional brand configuration
        
    Returns:
        Path to created brand directory
    """
    brand_dir = brands_root / brand_name
    brand_dir.mkdir(parents=True, exist_ok=True)
    
    # Create directory structure
    (brand_dir / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (brand_dir / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    (brand_dir / "templates").mkdir(parents=True, exist_ok=True)
    
    # Default config if none provided
    if config is None:
        config = {
            "brand": {
                "name": brand_name.replace("_", " ").title(),
                "tagline": "Test Brand",
                "website": f"https://{brand_name}.example.com"
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
                "stylesheet": "assets/style.css"
            }
        }
    
    # Write config file
    with open(brand_dir / "brand_config.yaml", "w") as f:
        yaml.dump(config, f)
    
    # Create basic assets
    create_test_assets(brand_dir / "assets")
    create_test_templates(brand_dir / "templates")
    
    return brand_dir


def create_test_assets(assets_dir: Path):
    """Create test assets (CSS, images, etc.)."""
    # Create CSS file
    css_content = """
    .brand-primary { color: #1E3A8A; }
    .brand-secondary { color: #3B82F6; }
    .brand-accent { color: #F59E0B; }
    
    body {
        font-family: Inter, sans-serif;
        margin: 0;
        padding: 20px;
    }
    
    header {
        border-bottom: 2px solid #1E3A8A;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    
    footer {
        border-top: 1px solid #ccc;
        padding-top: 10px;
        margin-top: 20px;
        text-align: center;
        color: #666;
    }
    """
    with open(assets_dir / "style.css", "w") as f:
        f.write(css_content)
    
    # Create test logo SVG
    logo_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
    <circle cx="50" cy="50" r="40" fill="#1E3A8A"/>
    <text x="50" y="55" text-anchor="middle" fill="white" font-family="Arial" font-size="14">LOGO</text>
</svg>"""
    with open(assets_dir / "images" / "logo.svg", "w") as f:
        f.write(logo_svg)


def create_test_templates(templates_dir: Path):
    """Create test HTML templates."""
    # Document template
    document_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title or "Document" }}</title>
    <style>{{ brand_css }}</style>
</head>
<body>
    <header>
        {% if assets.logo %}
        <img src="{{ assets.logo }}" alt="{{ brand.name }}" style="height: 50px;">
        {% endif %}
        <h1>{{ title or "Document" }}</h1>
        {% if author %}<p class="author">By {{ author }}</p>{% endif %}
    </header>
    
    <main>
        {{ content }}
    </main>
    
    <footer>
        <p>{{ brand.name }}{% if brand.website %} • {{ brand.website }}{% endif %}</p>
    </footer>
</body>
</html>"""
    with open(templates_dir / "document.html", "w") as f:
        f.write(document_template)
    
    # Letter template
    letter_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title or "Letter" }}</title>
    <style>{{ brand_css }}</style>
</head>
<body>
    <header>
        {% if assets.logo %}
        <img src="{{ assets.logo }}" alt="{{ brand.name }}" style="height: 40px; float: right;">
        {% endif %}
        <h2>{{ brand.name }}</h2>
        {% if brand.tagline %}<p>{{ brand.tagline }}</p>{% endif %}
    </header>
    
    <main>
        {% if date %}<p class="date">{{ date }}</p>{% endif %}
        {% if recipient %}<p class="recipient">{{ recipient }}</p>{% endif %}
        
        {{ content }}
        
        {% if signature %}
        <div class="signature">
            <p>{{ signature }}</p>
        </div>
        {% endif %}
    </main>
</body>
</html>"""
    with open(templates_dir / "letter.html", "w") as f:
        f.write(letter_template)


def assert_pdf_valid(pdf_path: Path):
    """Assert that a PDF file is valid and not empty."""
    assert pdf_path.exists(), f"PDF file not found: {pdf_path}"
    assert pdf_path.stat().st_size > 0, f"PDF file is empty: {pdf_path}"
    
    # Basic PDF header check
    with open(pdf_path, 'rb') as f:
        header = f.read(4)
        assert header == b'%PDF', f"Invalid PDF header: {pdf_path}"


def count_test_coverage(module_name: str) -> Dict[str, int]:
    """
    Helper to analyze test coverage for a module.
    This is a placeholder for coverage analysis.
    """
    # This would integrate with coverage.py in a real implementation
    return {
        "statements": 0,
        "missing": 0,
        "coverage": 0
    }