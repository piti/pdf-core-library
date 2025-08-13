# PDF Core Library

A comprehensive, open-source PDF generation library with professional templates and brand management capabilities.

## Features

### 🎨 Professional PDF Generation
- High-quality PDF output using Playwright engine
- Async/await support for scalable applications
- Multiple document templates (documents, letters, reports, invoices, etc.)
- Custom page layouts and professional formatting

### 🏢 Multi-Brand Support
- Isolated brand configurations with custom styling
- Brand-specific templates and assets
- Logo, font, and image management
- Brand protection and access controls

### 🛠️ Template System
- Jinja2-based template engine
- Responsive layouts for different page sizes
- Custom CSS injection and styling
- Extensible template architecture

### ☁️ Storage Abstraction
- Pluggable storage interface for extensibility
- Local filesystem implementation included
- Async file operations
- Asset optimization and processing

## Installation

```bash
pip install pdf-core
```

## Quick Start

```python
from pdf_core import BrandManager, TemplateEngine, AsyncPDFGenerator

# Load brand configuration
brand_manager = BrandManager()
brand = brand_manager.load_brand("example_company")

# Process content with frontmatter
content = """---
title: "My Document"
author: "John Doe"
template: "document"
---

# Introduction
This is a sample document with professional styling.

## Features
- Professional templates
- Brand consistency
- High-quality output
"""

# Generate PDF
template_engine = TemplateEngine()
rendered = template_engine.render_template(content, brand)

async with AsyncPDFGenerator() as generator:
    pdf_result = await generator.generate_pdf(rendered)
    print(f"Generated: {pdf_result.pdf_path}")
```

## Brand Configuration

Create professional brand configurations using YAML:

```yaml
brand:
  name: "Your Company"
  tagline: "Professional Excellence"
  website: "https://yourcompany.com"
  
colors:
  primary: "#1E3A8A"      # Professional Blue
  secondary: "#3B82F6"    # Lighter Blue
  accent: "#F59E0B"       # Accent Color
  
typography:
  primary_font: "Inter"
  secondary_font: "Source Sans Pro"
  
assets:
  logo: "assets/images/logo.svg"
  stylesheet: "assets/company_style.css"
```

## Template Development

Templates use Jinja2 syntax with full brand context:

```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ title or "Document" }}</title>
    <style>{{ stylesheet_content }}</style>
</head>
<body>
    <header>
        <img src="{{ brand.assets.logo }}" alt="{{ brand.name }}">
        <h1>{{ title }}</h1>
        {% if author %}<p>By {{ author }}</p>{% endif %}
    </header>
    
    <main>
        {{ html_content }}
    </main>
    
    <footer>
        {{ brand.name }}{% if brand.website %} • {{ brand.website }}{% endif %}
    </footer>
</body>
</html>
```

## Advanced Usage

### Custom Storage Backends

```python
from pdf_core.services import LocalStorage, StorageInterface

# Use default local storage
brand_manager = BrandManager()

# Use custom storage location
local_storage = LocalStorage("/path/to/storage")
brand_manager = BrandManager(storage=local_storage)

# Extend with custom storage (implement StorageInterface)
class CustomStorage(StorageInterface):
    async def upload_file(self, file_path, key, metadata=None):
        # Your custom implementation
        pass
```

## Development

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Code formatting
black src/ tests/
```

## Architecture

```
pdf-core/
├── core/                    # Core business logic
│   ├── brand_manager.py     # Brand configuration
│   ├── template_engine.py   # Template rendering
│   ├── pdf_generator.py     # PDF generation (sync)
│   └── async_pdf_generator.py  # PDF generation (async)
├── services/                # Storage services
│   └── storage_abstraction.py   # Storage interface and local implementation
└── utils/                   # Shared utilities
```

## Examples

See the `/docs/examples/` directory for:
- Basic PDF generation
- Custom brand setup
- Template development
- Library integration patterns
- Performance optimization

## License

MIT License - see LICENSE file for details.

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/piti/pdf-core-library/issues)
- 💬 [Discussions](https://github.com/piti/pdf-core-library/discussions)

## Roadmap

- [ ] WebP and AVIF image format support
- [ ] Template preview generation system
- [ ] Performance regression testing
- [ ] Template marketplace integration
- [ ] Advanced typography controls
- [ ] Interactive PDF elements