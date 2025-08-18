"""
PDF Core Library

A comprehensive PDF generation library with professional templates and brand management.

Main exports:
- BrandManager: Brand configuration and asset management
- PDFGenerator: Synchronous PDF generation
- AsyncPDFGenerator: Asynchronous PDF generation  
- TemplateEngine: Template rendering engine
- StorageInterface: Storage abstraction
- LocalStorage: Local filesystem storage
"""

from .core import BrandManager, InputProcessor, PDFGenerator, AsyncPDFGenerator, TemplateEngine, ProcessedInput, RenderedTemplate, PDFOutput
from .services import StorageInterface, LocalStorage

__version__ = "1.0.0"

__all__ = [
    "BrandManager",
    "InputProcessor",
    "PDFGenerator", 
    "AsyncPDFGenerator",
    "TemplateEngine",
    "ProcessedInput",
    "RenderedTemplate",
    "PDFOutput",
    "StorageInterface",
    "LocalStorage"
]
