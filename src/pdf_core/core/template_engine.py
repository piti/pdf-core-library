"""
Template engine module for PDF Pipeline.

Handles Jinja2 template processing, brand variable injection, and HTML generation
for PDF conversion.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

from .content_types import ProcessedInput, RenderedTemplate
from .brand_manager import BrandConfig

logger = logging.getLogger(__name__)



class TemplateEngine:
    """
    Processes Jinja2 templates with brand variables and content integration.
    
    Features:
    - Template selection logic (document, cover, letter, report)
    - Brand variable injection from BrandConfig
    - Content integration from InputProcessor
    - HTML generation with embedded CSS
    - Custom template functions and filters
    """
    
    def __init__(self, template_dirs: Optional[list] = None):
        """
        Initialize the TemplateEngine.
        
        Args:
            template_dirs: List of directories to search for templates.
                          If None, uses brand-specific template directories.
        """
        self.template_dirs = template_dirs or []
        self.jinja_env = None
        self._setup_jinja_environment()
        
    def _setup_jinja_environment(self) -> None:
        """Set up Jinja2 environment with custom filters and functions."""
        # Will be configured dynamically when rendering
        # since template directories are brand-specific
        pass
        
    def _configure_jinja_for_brand(self, brand_config: BrandConfig) -> None:
        """
        Configure Jinja2 environment for specific brand.
        
        Args:
            brand_config: Brand configuration containing template paths
        """
        template_dirs = []
        
        # Add brand-specific template directory
        brand_templates_dir = brand_config.brand_path / "templates"
        if brand_templates_dir.exists():
            template_dirs.append(str(brand_templates_dir))
            
        # Add any additional template directories
        template_dirs.extend(self.template_dirs)
        
        if not template_dirs:
            raise ValueError("No template directories found")
            
        # Create Jinja2 environment
        loader = FileSystemLoader(template_dirs)
        self.jinja_env = Environment(
            loader=loader,
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.jinja_env.filters['default'] = self._default_filter
        
        # Add custom functions
        self.jinja_env.globals['format_date'] = self._format_date
        
    def _default_filter(self, value, default_value=""):
        """Custom default filter that handles None and empty strings."""
        if value is None or value == "":
            return default_value
        return value
        
    def _format_date(self, date_value, format_string="%B %Y"):
        """Format date values for template display."""
        if not date_value:
            return ""
        
        # Handle various date formats
        if isinstance(date_value, str):
            # Simple year handling
            if date_value.isdigit() and len(date_value) == 4:
                return date_value
            return date_value
            
        # Could add more sophisticated date parsing here
        return str(date_value)
        
    def render_template(
        self,
        processed_input: ProcessedInput,
        brand_config: BrandConfig,
        template_type: str = "document",
        template_options: Optional[Dict[str, Any]] = None
    ) -> RenderedTemplate:
        """
        Render a template with processed input and brand configuration.
        
        Args:
            processed_input: Processed markdown input from InputProcessor
            brand_config: Brand configuration from BrandManager
            template_type: Type of template to use (document, cover, letter, report)
            template_options: Additional options for template rendering
            
        Returns:
            RenderedTemplate object with final HTML content
            
        Raises:
            TemplateNotFound: If specified template doesn't exist
            ValueError: If template configuration is invalid
        """
        # Configure Jinja2 for this brand
        self._configure_jinja_for_brand(brand_config)
        
        # Get template filename
        template_filename = self._get_template_filename(brand_config, template_type)
        
        try:
            template = self.jinja_env.get_template(template_filename)
        except TemplateNotFound as e:
            logger.error(f"Template not found: {template_filename}")
            raise TemplateNotFound(f"Template not found: {template_filename}")
            
        # Prepare template context
        context = self._build_template_context(
            processed_input, brand_config, template_type, template_options
        )
        
        # Render the template
        try:
            html_content = template.render(context)
            logger.info(f"Successfully rendered template: {template_filename}")
            
            # Create rendered template object
            rendered = RenderedTemplate(
                html_content=html_content,
                css_embedded=True,  # CSS is embedded via brand_css variable
                metadata={
                    "title": processed_input.title,
                    "author": processed_input.author,
                    "date": processed_input.date,
                    "brand": brand_config.name,
                    "template_type": template_type,
                    "word_count": processed_input.word_count
                },
                template_name=template_filename
            )
            
            return rendered
            
        except Exception as e:
            logger.error(f"Failed to render template {template_filename}: {e}")
            raise ValueError(f"Template rendering failed: {e}")
            
    def _get_template_filename(self, brand_config: BrandConfig, template_type: str) -> str:
        """
        Get the appropriate template filename for the given type.
        
        Args:
            brand_config: Brand configuration
            template_type: Type of template requested
            
        Returns:
            Template filename
        """
        # Check if specific template is configured in brand
        if template_type in brand_config.templates:
            template_filename = brand_config.templates[template_type]
            
            # Handle relative paths
            if not template_filename.endswith('.html'):
                template_filename += '.html'
                
            return template_filename
        
        # Use default template mapping
        template_mapping = {
            "document": "document.html",
            "cover": "cover.html", 
            "letter": "letter.html",
            "report": "report.html",
            "checklist": "checklist.html",
            "invoice": "invoice.html",
            "presentation": "presentation.html", 
            "contract": "contract.html",
            "newsletter": "newsletter.html",
            "brochure": "brochure.html",
            "proposal": "proposal.html"
        }
        
        if template_type not in template_mapping:
            logger.warning(f"Unknown template type: {template_type}, using 'document'")
            template_type = "document"
            
        return template_mapping[template_type]
        
    def _build_template_context(
        self,
        processed_input: ProcessedInput,
        brand_config: BrandConfig,
        template_type: str,
        template_options: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build the context dictionary for template rendering.
        
        Args:
            processed_input: Processed input data
            brand_config: Brand configuration
            template_type: Template type being rendered
            template_options: Additional template options
            
        Returns:
            Dictionary containing all template variables
        """
        context = {}
        
        # Add content from processed input
        context.update({
            "title": processed_input.title,
            "subtitle": processed_input.metadata.get("subtitle"),
            "author": processed_input.author,
            "date": processed_input.date,
            "content": processed_input.html_content,
            "word_count": processed_input.word_count,
            "metadata": processed_input.metadata
        })
        
        # Add brand information
        context.update({
            "brand": {
                "name": brand_config.name,
                "tagline": brand_config.tagline,
                "website": brand_config.website,
                "community": brand_config.community,
                "colors": brand_config.colors,
                "typography": brand_config.typography
            },
            "assets": brand_config.assets
        })
        
        # Add CSS variables and styling
        context.update({
            "brand_css": self._build_complete_css(brand_config),
            "css_variables": brand_config.css_variables
        })
        
        # Add template-specific options
        template_config = brand_config.template_options.get(template_type, {})
        context.update(template_config)
        
        # Add full template_options structure for template conditionals
        context["template_options"] = brand_config.template_options
        
        # Add user-provided template options
        if template_options:
            context.update(template_options)
            
        logger.debug(f"Built template context with {len(context)} variables")
        return context
        
    def _build_complete_css(self, brand_config: BrandConfig) -> str:
        """
        Build complete CSS including variables and brand stylesheet.
        
        Args:
            brand_config: Brand configuration
            
        Returns:
            Complete CSS string
        """
        css_parts = []
        
        # Add CSS variables
        if brand_config.css_variables:
            css_parts.append(brand_config.css_variables)
            
        # Add brand-specific CSS file content
        css_file_path = brand_config.assets.get("css")
        if css_file_path:
            css_path = Path(css_file_path)
            if css_path.exists():
                try:
                    with open(css_path, 'r', encoding='utf-8') as f:
                        css_content = f.read()
                        css_parts.append(css_content)
                        logger.debug(f"Loaded CSS from: {css_path}")
                except Exception as e:
                    logger.warning(f"Failed to load CSS file {css_path}: {e}")
            else:
                logger.warning(f"CSS file not found: {css_path}")
                
        # Add default PDF-friendly styles
        css_parts.append(self._get_default_pdf_styles())
        
        return "\n\n".join(css_parts)
        
    def _get_default_pdf_styles(self) -> str:
        """
        Get default PDF-friendly CSS styles.
        
        Returns:
            Default CSS styles for PDF generation
        """
        return """
/* Default PDF-friendly styles */
body {
    line-height: 1.4;
    color: #333;
    font-size: 11pt;
    max-width: none;
}

.page-break {
    page-break-before: always;
}

.no-break {
    page-break-inside: avoid;
}

h1, h2, h3, h4, h5, h6 {
    page-break-after: avoid;
    margin-top: 1em;
    margin-bottom: 0.5em;
}

.emergency-callout {
    background-color: var(--color-error-light, #FEE2E2);
    border-left: 4px solid var(--color-error, #EF4444);
    padding: 1em;
    margin: 1em 0;
    page-break-inside: avoid;
}

.highlight {
    background-color: var(--color-warning-light, #FEF3C7);
    padding: 0.2em 0.4em;
    border-radius: 3px;
}

.brand-cta {
    background-color: var(--color-primary, #1E3A8A);
    color: white;
    padding: 1em;
    text-align: center;
    margin: 1.5em 0;
    border-radius: 5px;
    page-break-inside: avoid;
}

.checklist-item {
    margin: 0.5em 0;
    padding-left: 1.5em;
    text-indent: -1.5em;
}

.checklist-item.checked {
    color: var(--color-success, #10B981);
}

.footer {
    margin-top: 2em;
    padding-top: 1em;
    border-top: 1px solid var(--color-text-light, #6B7280);
    font-size: 0.9em;
    color: var(--color-text-light, #6B7280);
}
"""
        
    def get_available_templates(self, brand_config: BrandConfig) -> list:
        """
        Get list of available templates for a brand.
        
        Args:
            brand_config: Brand configuration
            
        Returns:
            List of available template names
        """
        self._configure_jinja_for_brand(brand_config)
        
        available = []
        
        # Check configured templates
        for template_type, template_file in brand_config.templates.items():
            try:
                self.jinja_env.get_template(template_file)
                available.append(template_type)
            except TemplateNotFound:
                logger.warning(f"Configured template not found: {template_file}")
                
        # Check standard templates
        standard_templates = [
            "document.html", "cover.html", "letter.html", "report.html", "checklist.html",
            "invoice.html", "presentation.html", "contract.html", "newsletter.html", 
            "brochure.html", "proposal.html"
        ]
        for template_file in standard_templates:
            try:
                self.jinja_env.get_template(template_file)
                template_name = template_file.replace('.html', '')
                if template_name not in available:
                    available.append(template_name)
            except TemplateNotFound:
                pass
                
        return sorted(available)
        
    def validate_template(self, brand_config: BrandConfig, template_type: str) -> list:
        """
        Validate a template for completeness and syntax.
        
        Args:
            brand_config: Brand configuration
            template_type: Template type to validate
            
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        try:
            self._configure_jinja_for_brand(brand_config)
            template_filename = self._get_template_filename(brand_config, template_type)
            template = self.jinja_env.get_template(template_filename)
            
            # Check for required template variables
            source = self.jinja_env.loader.get_source(self.jinja_env, template_filename)
            template_source = source[0]
            
            required_vars = ["content", "brand", "title"]
            for var in required_vars:
                if f"{{{{ {var}" not in template_source and f"{{%- {var}" not in template_source:
                    warnings.append(f"Template may be missing required variable: {var}")
                    
        except TemplateNotFound:
            warnings.append(f"Template not found: {template_type}")
        except Exception as e:
            warnings.append(f"Template validation error: {e}")
            
        return warnings