"""
PDF generation module for PDF Pipeline.

Handles Playwright browser integration and HTML to PDF conversion with
print optimization and brand-specific formatting.
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field

from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from .template_engine import RenderedTemplate

logger = logging.getLogger(__name__)


@dataclass
class PDFConfig:
    """Configuration for PDF generation settings."""
    
    # Page format and layout
    format: str = "Letter"  # A4, Legal, Tabloid, etc.
    width: Optional[str] = None  # e.g., "8.5in" - overrides format
    height: Optional[str] = None  # e.g., "11in" - overrides format
    
    # Margins
    margin_top: str = "1in"
    margin_right: str = "1in"
    margin_bottom: str = "1in"  
    margin_left: str = "1in"
    
    # Print settings
    print_background: bool = True
    landscape: bool = False
    prefer_css_page_size: bool = True
    
    # Quality settings
    scale: float = 1.0  # 0.1 to 2.0
    
    # Output settings
    output_path: Optional[Path] = None
    
    # Browser settings
    timeout: int = 30000  # milliseconds
    wait_for_fonts: int = 2000  # milliseconds to wait for font loading
    
    # Additional PDF metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class GeneratedPDF:
    """Represents a generated PDF with metadata."""
    
    pdf_path: Path
    file_size: int
    page_count: int = 0
    generation_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PDFGenerator:
    """
    Generates PDFs from HTML using Playwright and Chromium.
    
    Features:
    - High-quality PDF generation with Chromium rendering
    - Print optimization for professional documents  
    - Configurable page formats, margins, and print settings
    - Font loading and CSS rendering support
    - Error handling for browser issues
    - Batch PDF generation capability
    """
    
    def __init__(self, headless: bool = True, browser_args: Optional[list] = None):
        """
        Initialize the PDFGenerator.
        
        Args:
            headless: Whether to run browser in headless mode
            browser_args: Additional browser launch arguments
        """
        self.headless = headless
        self.browser_args = browser_args or []
        self.playwright = None
        self.browser = None
        
    def __enter__(self):
        """Context manager entry - start browser."""
        self._start_browser()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop browser."""
        self._stop_browser()
        
    def _start_browser(self) -> None:
        """Start Playwright browser instance."""
        try:
            self.playwright = sync_playwright().start()
            
            # Launch browser with optimized settings for PDF generation
            launch_options = {
                'headless': self.headless,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--font-render-hinting=none',
                    '--disable-font-subpixel-positioning',
                ] + self.browser_args
            }
            
            self.browser = self.playwright.chromium.launch(**launch_options)
            logger.info("Browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise RuntimeError(f"Browser startup failed: {e}")
            
    def _stop_browser(self) -> None:
        """Stop Playwright browser instance."""
        try:
            if self.browser:
                self.browser.close()
                logger.debug("Browser stopped")
        except Exception as e:
            logger.warning(f"Error stopping browser: {e}")
        finally:
            self.browser = None
                
        try:
            if self.playwright:
                self.playwright.stop()
                logger.debug("Playwright stopped")
        except Exception as e:
            logger.warning(f"Error stopping playwright: {e}")
        finally:
            self.playwright = None
            
    def generate_pdf(
        self,
        rendered_template: RenderedTemplate,
        pdf_config: Optional[PDFConfig] = None,
        output_path: Optional[Union[str, Path]] = None
    ) -> GeneratedPDF:
        """
        Generate PDF from rendered template.
        
        Args:
            rendered_template: Rendered HTML template from TemplateEngine
            pdf_config: PDF generation configuration
            output_path: Output file path (overrides config)
            
        Returns:
            GeneratedPDF object with metadata
            
        Raises:
            RuntimeError: If browser is not started or PDF generation fails
            PlaywrightTimeoutError: If page loading times out
        """
        if not self.browser:
            raise RuntimeError("Browser not started. Use context manager or call _start_browser()")
            
        config = pdf_config or PDFConfig()
        
        # Determine output path
        if output_path:
            final_output_path = Path(output_path)
        elif config.output_path:
            final_output_path = config.output_path
        else:
            # Generate temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            final_output_path = Path(temp_file.name)
            temp_file.close()
            
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        
        start_time = __import__('time').time()
        
        try:
            # Create new page with optimized settings
            page = self.browser.new_page()
            
            # Set viewport for consistent rendering
            page.set_viewport_size({"width": 1200, "height": 1600})
            
            # Configure page for PDF generation
            self._configure_page_for_pdf(page)
            
            # Load HTML content
            logger.info("Loading HTML content into browser")
            page.set_content(rendered_template.html_content, wait_until="networkidle", timeout=config.timeout)
            
            # Wait for fonts to load
            if config.wait_for_fonts > 0:
                logger.debug(f"Waiting {config.wait_for_fonts}ms for fonts to load")
                page.wait_for_timeout(config.wait_for_fonts)
            
            # Generate PDF
            logger.info(f"Generating PDF: {final_output_path}")
            pdf_options = self._build_pdf_options(config, rendered_template)
            
            pdf_bytes = page.pdf(**pdf_options)
            
            # Write PDF to file
            with open(final_output_path, 'wb') as f:
                f.write(pdf_bytes)
                
            page.close()
            
            generation_time = __import__('time').time() - start_time
            file_size = final_output_path.stat().st_size
            
            logger.info(f"PDF generated successfully: {file_size} bytes in {generation_time:.2f}s")
            
            # Create result object
            generated_pdf = GeneratedPDF(
                pdf_path=final_output_path,
                file_size=file_size,
                generation_time=generation_time,
                metadata={
                    'template_name': rendered_template.template_name,
                    'original_title': rendered_template.metadata.get('title'),
                    'brand': rendered_template.metadata.get('brand'),
                    'word_count': rendered_template.metadata.get('word_count'),
                    'config': config.__dict__
                }
            )
            
            return generated_pdf
            
        except PlaywrightTimeoutError as e:
            logger.error(f"PDF generation timeout: {e}")
            raise PlaywrightTimeoutError(f"PDF generation timed out after {config.timeout}ms")
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            # Clean up partial file
            if final_output_path.exists():
                final_output_path.unlink()
            raise RuntimeError(f"PDF generation failed: {e}")
            
    def _configure_page_for_pdf(self, page: Page) -> None:
        """
        Configure page settings optimized for PDF generation.
        
        Args:
            page: Playwright page instance
        """
        # Set media type to print for CSS @media print rules
        page.emulate_media(media="print")
        
        # Add custom styles for better PDF rendering
        page.add_style_tag(content="""
            @page {
                -webkit-print-color-adjust: exact;
                color-adjust: exact;
            }
            
            body {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            
            * {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
        """)
        
    def _build_pdf_options(self, config: PDFConfig, rendered_template: RenderedTemplate) -> Dict[str, Any]:
        """
        Build PDF options dictionary from config and template.
        
        Args:
            config: PDF configuration
            rendered_template: Rendered template with metadata
            
        Returns:
            Dictionary of PDF options for Playwright
        """
        options = {
            'print_background': config.print_background,
            'landscape': config.landscape,
            'prefer_css_page_size': config.prefer_css_page_size,
            'scale': config.scale,
            'margin': {
                'top': config.margin_top,
                'right': config.margin_right,
                'bottom': config.margin_bottom,
                'left': config.margin_left,
            }
        }
        
        # Set page format or custom dimensions
        if config.width and config.height:
            options['width'] = config.width
            options['height'] = config.height
        else:
            options['format'] = config.format
            
        # Add PDF metadata if available
        title = rendered_template.metadata.get('title')
        author = rendered_template.metadata.get('author')
        
        if title:
            # Note: Playwright doesn't directly support PDF metadata
            # but we could add it via other means if needed
            pass
            
        logger.debug(f"PDF options: {options}")
        return options
        
    def generate_batch_pdfs(
        self,
        templates_and_configs: list,
        output_directory: Optional[Path] = None
    ) -> list:
        """
        Generate multiple PDFs in batch.
        
        Args:
            templates_and_configs: List of (RenderedTemplate, PDFConfig, filename) tuples
            output_directory: Directory for output files
            
        Returns:
            List of GeneratedPDF objects
        """
        if not self.browser:
            raise RuntimeError("Browser not started. Use context manager or call _start_browser()")
            
        results = []
        output_dir = output_directory or Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, (template, config, filename) in enumerate(templates_and_configs):
            try:
                output_path = output_dir / filename
                logger.info(f"Generating PDF {i+1}/{len(templates_and_configs)}: {filename}")
                
                result = self.generate_pdf(template, config, output_path)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to generate PDF {filename}: {e}")
                # Continue with remaining PDFs
                
        logger.info(f"Batch generation complete: {len(results)}/{len(templates_and_configs)} successful")
        return results
        
    def validate_pdf_config(self, config: PDFConfig) -> list:
        """
        Validate PDF configuration for common issues.
        
        Args:
            config: PDF configuration to validate
            
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        # Check page format
        valid_formats = ['Letter', 'Legal', 'Tabloid', 'Ledger', 'A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6']
        if not config.width and not config.height and config.format not in valid_formats:
            warnings.append(f"Invalid page format: {config.format}. Valid formats: {valid_formats}")
            
        # Check scale
        if not (0.1 <= config.scale <= 2.0):
            warnings.append(f"Scale should be between 0.1 and 2.0, got: {config.scale}")
            
        # Check timeout
        if config.timeout < 1000:
            warnings.append(f"Timeout seems too low: {config.timeout}ms. Consider at least 5000ms.")
        elif config.timeout > 300000:
            warnings.append(f"Timeout seems too high: {config.timeout}ms. Consider under 300000ms.")
            
        # Check output path
        if config.output_path and not config.output_path.parent.exists():
            warnings.append(f"Output directory doesn't exist: {config.output_path.parent}")
            
        return warnings