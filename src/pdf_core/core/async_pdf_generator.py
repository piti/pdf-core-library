"""
Async PDF generation module for PDF Pipeline.

Handles Playwright browser integration and HTML to PDF conversion with
print optimization and brand-specific formatting using async API.
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from .template_engine import RenderedTemplate
from .pdf_generator import PDFConfig, GeneratedPDF  # Import existing dataclasses

logger = logging.getLogger(__name__)


class AsyncPDFGenerator:
    """
    Async version of PDFGenerator that works within asyncio event loops.
    
    Features:
    - High-quality PDF generation with Chromium rendering
    - Print optimization for professional documents  
    - Configurable page formats, margins, and print settings
    - Font loading and CSS rendering support
    - Error handling for browser issues
    - Async/await compatibility
    """
    
    def __init__(self, headless: bool = True, browser_args: Optional[list] = None):
        """
        Initialize the AsyncPDFGenerator.
        
        Args:
            headless: Whether to run browser in headless mode
            browser_args: Additional browser launch arguments
        """
        self.headless = headless
        self.browser_args = browser_args or []
        self.playwright = None
        self.browser = None
        
    async def __aenter__(self):
        """Async context manager entry - start browser."""
        await self._start_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - stop browser."""
        await self._stop_browser()
        
    async def _start_browser(self) -> None:
        """Start Playwright browser instance."""
        try:
            self.playwright = await async_playwright().start()
            
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
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            logger.info("Async browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start async browser: {e}")
            raise RuntimeError(f"Async browser startup failed: {e}")
            
    async def _stop_browser(self) -> None:
        """Stop Playwright browser instance."""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                logger.debug("Async browser stopped")
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                logger.debug("Async playwright stopped")
                
        except Exception as e:
            logger.warning(f"Error stopping async browser: {e}")
            
    async def generate_pdf(
        self,
        rendered_template: RenderedTemplate,
        pdf_config: Optional[PDFConfig] = None,
        output_path: Optional[Union[str, Path]] = None
    ) -> GeneratedPDF:
        """
        Generate PDF from rendered template using async API.
        
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
            raise RuntimeError("Async browser not started. Use async context manager or call _start_browser()")
            
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
            page = await self.browser.new_page()
            
            # Set viewport for consistent rendering
            await page.set_viewport_size({"width": 1200, "height": 1600})
            
            # Configure page for PDF generation
            await self._configure_page_for_pdf(page)
            
            # Load HTML content
            logger.info("Loading HTML content into async browser")
            await page.set_content(rendered_template.html_content, wait_until="networkidle", timeout=config.timeout)
            
            # Wait for fonts to load
            if config.wait_for_fonts > 0:
                logger.debug(f"Waiting {config.wait_for_fonts}ms for fonts to load")
                await page.wait_for_timeout(config.wait_for_fonts)
            
            # Generate PDF
            logger.info(f"Generating PDF: {final_output_path}")
            pdf_options = self._build_pdf_options(config, rendered_template)
            
            pdf_bytes = await page.pdf(**pdf_options)
            
            # Write PDF to file
            with open(final_output_path, 'wb') as f:
                f.write(pdf_bytes)
                
            await page.close()
            
            generation_time = __import__('time').time() - start_time
            file_size = final_output_path.stat().st_size
            
            logger.info(f"Async PDF generated successfully: {file_size} bytes in {generation_time:.2f}s")
            
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
            logger.error(f"Async PDF generation timeout: {e}")
            raise PlaywrightTimeoutError(f"Async PDF generation timed out after {config.timeout}ms")
        except Exception as e:
            logger.error(f"Async PDF generation failed: {e}")
            # Clean up partial file
            if final_output_path.exists():
                final_output_path.unlink()
            raise RuntimeError(f"Async PDF generation failed: {e}")
            
    async def _configure_page_for_pdf(self, page: Page) -> None:
        """
        Configure page settings optimized for PDF generation.
        
        Args:
            page: Playwright page instance
        """
        # Set media type to print for CSS @media print rules
        await page.emulate_media(media="print")
        
        # Add custom styles for better PDF rendering
        await page.add_style_tag(content="""
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
            
        logger.debug(f"Async PDF options: {options}")
        return options