"""
Enhanced asset processing utilities for PDF Pipeline.

Handles automatic asset encoding, optimization, validation, and batch processing.
"""

import base64
import hashlib
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    
logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Supported asset types."""
    LOGO = "logo"
    IMAGE = "image"
    FONT = "font"
    CSS = "css"
    ICON = "icon"
    BACKGROUND = "background"
    

class ImageFormat(Enum):
    """Supported image formats."""
    PNG = "png"
    JPEG = "jpeg"
    SVG = "svg"
    GIF = "gif"
    WEBP = "webp"


@dataclass
class ProcessedAsset:
    """Represents a processed asset ready for upload."""
    
    original_path: Path
    filename: str
    asset_type: AssetType
    mime_type: str
    original_size: int
    processed_size: int
    base64_data: str
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    optimized: bool = False
    optimization_savings: int = 0
    processing_time: float = 0.0
    warnings: List[str] = field(default_factory=list)
    
    @property
    def size_reduction_percent(self) -> float:
        """Calculate size reduction percentage."""
        if self.original_size == 0:
            return 0.0
        return ((self.original_size - self.processed_size) / self.original_size) * 100


class AssetProcessor:
    """
    Enhanced asset processor with automatic encoding and optimization.
    
    Features:
    - Automatic base64 encoding
    - Image optimization (resize, compress)
    - Format conversion
    - Batch processing
    - Integrity validation
    - Smart type detection
    """
    
    # Maximum sizes for different asset types (in bytes)
    MAX_SIZES = {
        AssetType.LOGO: 500 * 1024,      # 500KB for logos
        AssetType.IMAGE: 2 * 1024 * 1024,  # 2MB for images
        AssetType.ICON: 100 * 1024,      # 100KB for icons
        AssetType.BACKGROUND: 1024 * 1024,  # 1MB for backgrounds
        AssetType.FONT: 500 * 1024,      # 500KB for fonts
        AssetType.CSS: 100 * 1024,       # 100KB for CSS
    }
    
    # Target dimensions for optimization
    TARGET_DIMENSIONS = {
        AssetType.LOGO: (400, 200),      # Max width x height for logos
        AssetType.ICON: (128, 128),      # Square icons
        AssetType.BACKGROUND: (1920, 1080),  # Full HD backgrounds
        AssetType.IMAGE: (1200, 800),    # General images
    }
    
    # Supported file extensions by type
    SUPPORTED_EXTENSIONS = {
        AssetType.IMAGE: {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp'},
        AssetType.LOGO: {'.png', '.svg', '.jpg', '.jpeg'},
        AssetType.ICON: {'.png', '.svg', '.ico'},
        AssetType.BACKGROUND: {'.png', '.jpg', '.jpeg', '.webp'},
        AssetType.FONT: {'.woff', '.woff2', '.ttf', '.otf', '.eot'},
        AssetType.CSS: {'.css', '.scss', '.sass'},
    }
    
    def __init__(self, optimize_images: bool = True, 
                 convert_to_web_formats: bool = True,
                 max_image_dimension: int = 2048):
        """
        Initialize the asset processor.
        
        Args:
            optimize_images: Whether to optimize images
            convert_to_web_formats: Convert images to web-friendly formats
            max_image_dimension: Maximum dimension for image resizing
        """
        self.optimize_images = optimize_images and HAS_PIL
        self.convert_to_web_formats = convert_to_web_formats
        self.max_image_dimension = max_image_dimension
        
        if not HAS_PIL and optimize_images:
            logger.warning("PIL not installed. Image optimization disabled.")
    
    def process_asset(self, file_path: Union[str, Path], 
                      asset_type: Optional[AssetType] = None,
                      custom_name: Optional[str] = None,
                      optimize: Optional[bool] = None) -> ProcessedAsset:
        """
        Process a single asset file.
        
        Args:
            file_path: Path to the asset file
            asset_type: Type of asset (auto-detected if not provided)
            custom_name: Custom filename for the asset
            optimize: Override optimization setting
            
        Returns:
            ProcessedAsset object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type is not supported
        """
        import time
        start_time = time.time()
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Asset file not found: {file_path}")
        
        # Auto-detect asset type if not provided
        if asset_type is None:
            asset_type = self._detect_asset_type(file_path)
        
        # Validate file extension
        if not self._is_supported_extension(file_path, asset_type):
            raise ValueError(f"Unsupported file type for {asset_type.value}: {file_path.suffix}")
        
        # Get file info
        original_size = file_path.stat().st_size
        mime_type = self._get_mime_type(file_path)
        filename = custom_name or file_path.name
        
        # Process based on type
        if asset_type in [AssetType.IMAGE, AssetType.LOGO, AssetType.ICON, AssetType.BACKGROUND]:
            data, processed_size, metadata, warnings = self._process_image(
                file_path, asset_type, optimize if optimize is not None else self.optimize_images
            )
        else:
            # For non-image assets, just read and encode
            data, processed_size, metadata, warnings = self._process_other(file_path)
        
        # Calculate checksum
        checksum = hashlib.sha256(data).hexdigest()
        
        # Encode to base64
        base64_data = base64.b64encode(data).decode('utf-8')
        
        processing_time = time.time() - start_time
        
        return ProcessedAsset(
            original_path=file_path,
            filename=filename,
            asset_type=asset_type,
            mime_type=mime_type,
            original_size=original_size,
            processed_size=processed_size,
            base64_data=base64_data,
            checksum=checksum,
            metadata=metadata,
            optimized=optimize if optimize is not None else self.optimize_images,
            optimization_savings=original_size - processed_size,
            processing_time=processing_time,
            warnings=warnings
        )
    
    def process_batch(self, file_paths: List[Union[str, Path]], 
                     asset_type: Optional[AssetType] = None,
                     optimize: Optional[bool] = None) -> List[ProcessedAsset]:
        """
        Process multiple asset files.
        
        Args:
            file_paths: List of file paths to process
            asset_type: Type for all assets (auto-detected individually if not provided)
            optimize: Override optimization setting
            
        Returns:
            List of ProcessedAsset objects
        """
        processed = []
        
        for file_path in file_paths:
            try:
                asset = self.process_asset(file_path, asset_type, optimize=optimize)
                processed.append(asset)
                logger.info(f"Processed {file_path}: {asset.processed_size:,} bytes "
                          f"({asset.size_reduction_percent:.1f}% reduction)")
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                
        return processed
    
    def validate_asset(self, asset: ProcessedAsset) -> Tuple[bool, List[str]]:
        """
        Validate a processed asset.
        
        Args:
            asset: ProcessedAsset to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check size limits
        max_size = self.MAX_SIZES.get(asset.asset_type)
        if max_size and asset.processed_size > max_size:
            issues.append(f"Size {asset.processed_size:,} bytes exceeds limit of {max_size:,} bytes")
        
        # Check base64 encoding
        try:
            decoded = base64.b64decode(asset.base64_data)
            if hashlib.sha256(decoded).hexdigest() != asset.checksum:
                issues.append("Checksum mismatch after encoding")
        except Exception as e:
            issues.append(f"Invalid base64 encoding: {e}")
        
        # Check for warnings from processing
        if asset.warnings:
            issues.extend(asset.warnings)
        
        return len(issues) == 0, issues
    
    def _detect_asset_type(self, file_path: Path) -> AssetType:
        """Auto-detect asset type from file path and extension."""
        filename = file_path.name.lower()
        extension = file_path.suffix.lower()
        
        # Check by filename patterns
        if 'logo' in filename:
            return AssetType.LOGO
        elif 'icon' in filename or extension == '.ico':
            return AssetType.ICON
        elif 'background' in filename or 'bg' in filename:
            return AssetType.BACKGROUND
        elif extension in {'.woff', '.woff2', '.ttf', '.otf', '.eot'}:
            return AssetType.FONT
        elif extension in {'.css', '.scss', '.sass'}:
            return AssetType.CSS
        elif extension in {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp'}:
            return AssetType.IMAGE
        else:
            # Default to image for unknown types
            return AssetType.IMAGE
    
    def _is_supported_extension(self, file_path: Path, asset_type: AssetType) -> bool:
        """Check if file extension is supported for the asset type."""
        extension = file_path.suffix.lower()
        supported = self.SUPPORTED_EXTENSIONS.get(asset_type, set())
        return extension in supported
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type for a file."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            # Fallback for common types
            extension_map = {
                '.svg': 'image/svg+xml',
                '.woff': 'font/woff',
                '.woff2': 'font/woff2',
                '.ttf': 'font/ttf',
                '.otf': 'font/otf',
                '.css': 'text/css',
            }
            mime_type = extension_map.get(file_path.suffix.lower(), 'application/octet-stream')
        return mime_type
    
    def _process_image(self, file_path: Path, asset_type: AssetType, 
                      optimize: bool) -> Tuple[bytes, int, Dict[str, Any], List[str]]:
        """Process image assets with optional optimization."""
        warnings = []
        metadata = {}
        
        # For SVG files, just read as text
        if file_path.suffix.lower() == '.svg':
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Basic SVG optimization (remove comments, unnecessary whitespace)
            if optimize:
                try:
                    svg_text = data.decode('utf-8')
                    # Remove comments
                    import re
                    svg_text = re.sub(r'<!--.*?-->', '', svg_text, flags=re.DOTALL)
                    # Remove excessive whitespace
                    svg_text = re.sub(r'\s+', ' ', svg_text)
                    svg_text = svg_text.strip()
                    data = svg_text.encode('utf-8')
                except Exception as e:
                    warnings.append(f"SVG optimization failed: {e}")
            
            metadata['format'] = 'svg'
            return data, len(data), metadata, warnings
        
        # For raster images, use PIL if available
        if not HAS_PIL:
            # Without PIL, just read the file
            with open(file_path, 'rb') as f:
                data = f.read()
            metadata['format'] = file_path.suffix[1:].lower()
            return data, len(data), metadata, warnings
        
        # Process with PIL
        try:
            from io import BytesIO
            
            img = Image.open(file_path)
            original_format = img.format
            original_size = img.size
            
            metadata['original_dimensions'] = f"{original_size[0]}x{original_size[1]}"
            metadata['original_format'] = original_format
            
            if optimize:
                # Resize if needed
                target_dims = self.TARGET_DIMENSIONS.get(asset_type)
                if target_dims:
                    # Calculate scaling to fit within target dimensions
                    scale = min(
                        target_dims[0] / original_size[0],
                        target_dims[1] / original_size[1],
                        1.0  # Don't upscale
                    )
                    
                    if scale < 1.0:
                        new_size = (
                            int(original_size[0] * scale),
                            int(original_size[1] * scale)
                        )
                        img = img.resize(new_size, Image.Resampling.LANCZOS)
                        metadata['resized_to'] = f"{new_size[0]}x{new_size[1]}"
                        warnings.append(f"Image resized from {original_size} to {new_size}")
                
                # Convert RGBA to RGB for JPEG
                if original_format == 'PNG' and self.convert_to_web_formats:
                    # Check if image has transparency
                    if img.mode == 'RGBA':
                        # Keep PNG for transparent images
                        output_format = 'PNG'
                    else:
                        # Convert to JPEG for non-transparent images
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                        output_format = 'JPEG'
                else:
                    output_format = original_format or 'PNG'
                
                # Save optimized image
                output = BytesIO()
                save_kwargs = {
                    'format': output_format,
                    'optimize': True,
                }
                
                if output_format == 'JPEG':
                    save_kwargs['quality'] = 85
                    save_kwargs['progressive'] = True
                elif output_format == 'PNG':
                    save_kwargs['compress_level'] = 9
                
                img.save(output, **save_kwargs)
                data = output.getvalue()
                
                metadata['optimized_format'] = output_format
                metadata['optimized_dimensions'] = f"{img.size[0]}x{img.size[1]}"
            else:
                # No optimization, just read original
                with open(file_path, 'rb') as f:
                    data = f.read()
            
        except Exception as e:
            warnings.append(f"Image processing failed: {e}")
            # Fallback to reading raw file
            with open(file_path, 'rb') as f:
                data = f.read()
            
        return data, len(data), metadata, warnings
    
    def _process_other(self, file_path: Path) -> Tuple[bytes, int, Dict[str, Any], List[str]]:
        """Process non-image assets."""
        warnings = []
        metadata = {
            'format': file_path.suffix[1:].lower() if file_path.suffix else 'unknown'
        }
        
        # Read file
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # For CSS files, we could do minification
        if file_path.suffix.lower() == '.css':
            try:
                css_text = data.decode('utf-8')
                # Basic CSS minification (remove comments and excessive whitespace)
                import re
                # Remove comments
                css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
                # Remove excessive whitespace
                css_text = re.sub(r'\s+', ' ', css_text)
                css_text = css_text.strip()
                data = css_text.encode('utf-8')
                metadata['minified'] = True
            except Exception as e:
                warnings.append(f"CSS minification failed: {e}")
        
        return data, len(data), metadata, warnings


def create_optimized_processor() -> AssetProcessor:
    """Create an optimized asset processor with recommended settings."""
    return AssetProcessor(
        optimize_images=True,
        convert_to_web_formats=True,
        max_image_dimension=2048
    )