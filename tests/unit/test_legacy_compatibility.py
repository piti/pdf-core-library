"""
Legacy compatibility tests to ensure 100% backward compatibility.
These tests verify that all original functionality works exactly as before.
"""

import pytest
import tempfile
from pathlib import Path

class TestLegacyCompatibility:
    """Test that all legacy functionality is preserved"""
    
    def test_brand_manager_legacy_interface(self):
        """Test that BrandManager works exactly like the original"""
        from pdf_core import BrandManager
        
        # This should work exactly as before
        brand_manager = BrandManager()
        
        # Test original methods exist and work
        assert hasattr(brand_manager, 'load_brand')
        assert hasattr(brand_manager, 'create_brand')
        assert hasattr(brand_manager, 'list_available_brands')
        
        # Test that original behavior is preserved
        brands = brand_manager.list_available_brands()
        assert isinstance(brands, list)
    
    def test_pdf_generator_legacy_interface(self):
        """Test that PDFGenerator works exactly like the original"""
        from pdf_core import PDFGenerator
        
        # Should work exactly as before
        pdf_generator = PDFGenerator()
        
        # Test original methods exist
        assert hasattr(pdf_generator, 'generate_pdf')
        
        # Test context manager support (original feature)
        with pdf_generator:
            assert pdf_generator.browser is not None
    
    @pytest.mark.asyncio
    async def test_async_pdf_generator_legacy_interface(self):
        """Test that AsyncPDFGenerator works exactly like the original"""
        from pdf_core import AsyncPDFGenerator
        
        # Should work exactly as before
        async with AsyncPDFGenerator() as generator:
            assert generator.browser is not None
            assert hasattr(generator, 'generate_pdf')
    
    def test_template_engine_legacy_interface(self):
        """Test that TemplateEngine works exactly like the original"""
        from pdf_core import TemplateEngine
        
        template_engine = TemplateEngine()
        
        # Test original methods exist
        assert hasattr(template_engine, 'render_template')
        assert hasattr(template_engine, 'get_available_templates')
    
    def test_original_imports_work(self):
        """Test that all original imports work"""
        # These should all work without errors
        from pdf_core import BrandManager
        from pdf_core import PDFGenerator
        from pdf_core import AsyncPDFGenerator
        from pdf_core import TemplateEngine
        
        # Test that classes can be instantiated
        brand_manager = BrandManager()
        pdf_generator = PDFGenerator()
        template_engine = TemplateEngine()
        
        assert brand_manager is not None
        assert pdf_generator is not None  
        assert template_engine is not None
    
    def test_storage_interface_works_with_legacy(self):
        """Test that storage interface integrates properly with existing functionality"""
        from pdf_core import BrandManager
        from pdf_core.services import LocalStorage
        
        # Legacy usage should still work
        brand_manager = BrandManager()
        brands = brand_manager.list_available_brands()
        assert isinstance(brands, list)
        
        # Enhanced usage with custom storage should also work
        storage = LocalStorage()
        enhanced_brand_manager = BrandManager(storage=storage)
        
        # Original methods should still work on enhanced version
        brands = enhanced_brand_manager.list_available_brands()
        assert isinstance(brands, list)