"""
Brand management module for PDF Pipeline.

Handles loading brand configurations, validating assets, and generating CSS variables
for template processing.
"""

import json
import logging
import shutil
import tarfile
import hashlib
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

import yaml

logger = logging.getLogger(__name__)


class BrandManagerError(Exception):
    """Base exception for brand management operations."""
    pass


class BrandValidationError(BrandManagerError):
    """Exception raised when brand validation fails."""
    pass


class BrandNotFoundError(BrandManagerError):
    """Exception raised when requested brand doesn't exist."""
    pass


class BrandExistsError(BrandManagerError):
    """Exception raised when trying to create a brand that already exists."""
    pass


class BrandProtectionError(BrandManagerError):
    """Exception raised when trying to modify a protected brand."""
    pass


@dataclass
class BrandAsset:
    """Represents a brand asset with metadata."""
    
    path: Path
    asset_type: str  # 'logo', 'css', 'font', 'image', etc.
    file_size: int
    checksum: str
    uploaded_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class BrandTemplate:
    """Represents a brand template configuration."""
    
    name: str
    description: str
    category: str
    version: str
    config: Dict[str, Any]
    features: List[str] = field(default_factory=list)
    required_assets: List[str] = field(default_factory=list)
    optional_assets: List[str] = field(default_factory=list)


@dataclass
class BrandConfig:
    """Represents a loaded and processed brand configuration."""
    
    name: str
    tagline: str = ""
    website: str = ""
    community: str = ""
    
    # Color configuration
    colors: Dict[str, str] = field(default_factory=dict)
    
    # Typography configuration  
    typography: Dict[str, Any] = field(default_factory=dict)
    
    # Layout configuration
    layout: Dict[str, str] = field(default_factory=dict)
    
    # Asset paths (validated)
    assets: Dict[str, str] = field(default_factory=dict)
    
    # Template configuration
    templates: Dict[str, str] = field(default_factory=dict)
    template_options: Dict[str, Any] = field(default_factory=dict)
    
    # PDF-specific settings
    pdf_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Compliance rules
    compliance: Dict[str, Any] = field(default_factory=dict)
    
    # Brand metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Generated CSS variables
    css_variables: str = ""
    
    # Brand directory path
    brand_path: Path = field(default_factory=Path)
    
    # Enhanced tracking fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    template_source: Optional[str] = None
    status: str = "active"
    version: str = "1.0.0"
    
    # Protection fields
    is_protected: bool = False
    protection_level: str = "none"  # "none", "warn", "strict"
    protected_by: Optional[str] = None
    protected_at: Optional[datetime] = None
    protection_reason: str = ""


class BrandManager:
    """
    Manages brand configurations and asset validation.
    
    Features:
    - YAML brand configuration loading and CRUD operations
    - Asset path validation with graceful error handling  
    - CSS variable generation from brand configuration
    - Template and PDF settings management
    - Brand creation, update, deletion with safety checks
    - Asset management and integrity validation
    - Template system for brand inheritance
    """
    
    def __init__(self, brands_root: Optional[Path] = None, templates_root: Optional[Path] = None, storage=None):
        """
        Initialize the BrandManager.
        
        Args:
            brands_root: Root directory containing brand configurations.
                        Defaults to config/brands/
            templates_root: Root directory containing brand templates.
                           Defaults to config/templates/
            storage: Optional storage interface for advanced use cases.
                    For future extensibility.
        """
        self.brands_root = brands_root or Path("config/brands")
        self.templates_root = templates_root or Path("config/templates")
        self.storage = storage  # Store for future extensibility
        
        # Create directories if they don't exist
        self.brands_root.mkdir(parents=True, exist_ok=True)
        self.templates_root.mkdir(parents=True, exist_ok=True)
            
    def load_brand(self, brand_name: str) -> BrandConfig:
        """
        Load and process a brand configuration.
        
        Args:
            brand_name: Name of the brand to load (directory name)
            
        Returns:
            BrandConfig object with loaded configuration and generated CSS
            
        Raises:
            FileNotFoundError: If brand configuration file doesn't exist
            ValueError: If brand configuration is invalid
        """
        brand_path = self.brands_root / brand_name
        config_path = brand_path / "brand_config.yaml"
        
        if not config_path.exists():
            raise BrandNotFoundError(f"Brand configuration not found: {config_path}")
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
                
            if not raw_config:
                raise BrandValidationError("Empty brand configuration")
                
            # Extract configuration sections
            brand_info = raw_config.get('brand', {})
            colors = raw_config.get('colors', {})
            typography = raw_config.get('typography', {})
            layout = raw_config.get('layout', {})
            assets = raw_config.get('assets', {})
            templates = raw_config.get('templates', {})
            template_options = raw_config.get('template_options', {})
            pdf_settings = raw_config.get('pdf_settings', {})
            compliance = raw_config.get('compliance', {})
            metadata = raw_config.get('metadata', {})
            
            # Parse datetime fields if present
            created_at = None
            updated_at = None
            protected_at = None
            
            if metadata.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(metadata['created_at'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid created_at timestamp in {brand_name}")
                    
            if metadata.get('updated_at'):
                try:
                    updated_at = datetime.fromisoformat(metadata['updated_at'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid updated_at timestamp in {brand_name}")
                    
            if raw_config.get('protected_at'):
                try:
                    protected_at = datetime.fromisoformat(raw_config['protected_at'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid protected_at timestamp in {brand_name}")
            
            # Create BrandConfig object
            brand_config = BrandConfig(
                name=brand_info.get('name', brand_name),
                tagline=brand_info.get('tagline', ''),
                website=brand_info.get('website', ''),
                community=brand_info.get('community', ''),
                colors=colors,
                typography=typography,
                layout=layout,
                assets=assets,
                templates=templates,
                template_options=template_options,
                pdf_settings=pdf_settings,
                compliance=compliance,
                metadata=metadata,
                brand_path=brand_path,
                created_at=created_at,
                updated_at=updated_at,
                template_source=metadata.get('template_source'),
                status=metadata.get('status', 'active'),
                version=metadata.get('version', '1.0.0'),
                # Protection fields
                is_protected=raw_config.get('is_protected', False),
                protection_level=raw_config.get('protection_level', 'none'),
                protected_by=raw_config.get('protected_by'),
                protected_at=protected_at,
                protection_reason=raw_config.get('protection_reason', '')
            )
            
            # Validate assets and update paths
            self._validate_assets(brand_config)
            
            # Generate CSS variables
            brand_config.css_variables = self._generate_css_variables(brand_config)
            
            logger.info(f"Successfully loaded brand: {brand_config.name}")
            return brand_config
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in brand config {config_path}: {e}")
            raise BrandValidationError(f"Invalid brand configuration: {e}")
        except Exception as e:
            logger.error(f"Failed to load brand {brand_name}: {e}")
            raise BrandValidationError(f"Failed to load brand configuration: {e}")
            
    def _validate_assets(self, brand_config: BrandConfig) -> None:
        """
        Validate that brand assets exist and update paths to be absolute.
        
        Args:
            brand_config: BrandConfig object to validate and update
        """
        validated_assets = {}
        
        for asset_key, asset_value in brand_config.assets.items():
            if not asset_value:
                logger.warning(f"Empty asset path for {asset_key}")
                continue
                
            # Handle font list (special case)
            if asset_key == 'fonts' and isinstance(asset_value, list):
                validated_fonts = []
                for font_path in asset_value:
                    if not font_path:
                        continue
                        
                    if not Path(font_path).is_absolute():
                        full_path = brand_config.brand_path / font_path
                    else:
                        full_path = Path(font_path)
                        
                    if full_path.exists():
                        validated_fonts.append(str(full_path))
                        logger.debug(f"Validated font: {full_path}")
                    else:
                        logger.warning(f"Font not found: {full_path}")
                        validated_fonts.append(str(full_path))  # Graceful degradation
                        
                validated_assets[asset_key] = validated_fonts
            else:
                # Handle single asset path
                asset_path = str(asset_value)  # Ensure it's a string
                
                # Convert relative path to absolute path within brand directory
                if not Path(asset_path).is_absolute():
                    full_path = brand_config.brand_path / asset_path
                else:
                    full_path = Path(asset_path)
                    
                if full_path.exists():
                    validated_assets[asset_key] = str(full_path)
                    logger.debug(f"Validated asset {asset_key}: {full_path}")
                else:
                    logger.warning(f"Asset not found {asset_key}: {full_path}")
                    # Include path anyway for graceful degradation
                    validated_assets[asset_key] = str(full_path)
            
        brand_config.assets = validated_assets
        
    def _generate_css_variables(self, brand_config: BrandConfig) -> str:
        """
        Generate CSS custom properties from brand configuration.
        
        Args:
            brand_config: BrandConfig object to process
            
        Returns:
            CSS string with custom properties
        """
        css_lines = [":root {"]
        
        # Generate color variables
        for color_name, color_value in brand_config.colors.items():
            css_name = color_name.replace('_', '-')
            css_lines.append(f"  --color-{css_name}: {color_value};")
            
        # Generate typography variables
        typography = brand_config.typography
        if 'primary_font' in typography:
            css_lines.append(f"  --font-primary: '{typography['primary_font']}', {typography.get('fallback', 'sans-serif')};")
        if 'secondary_font' in typography:
            css_lines.append(f"  --font-secondary: '{typography['secondary_font']}', {typography.get('fallback', 'sans-serif')};")
            
        # Generate font size variables
        if 'sizes' in typography:
            for size_name, size_value in typography['sizes'].items():
                css_name = size_name.replace('_', '-')
                css_lines.append(f"  --font-size-{css_name}: {size_value};")
                
        # Generate font weight variables  
        if 'weights' in typography:
            for weight_name, weight_value in typography['weights'].items():
                css_name = weight_name.replace('_', '-')
                css_lines.append(f"  --font-weight-{css_name}: {weight_value};")
                
        # Generate layout variables
        for layout_name, layout_value in brand_config.layout.items():
            css_name = layout_name.replace('_', '-')
            css_lines.append(f"  --layout-{css_name}: {layout_value};")
            
        css_lines.append("}")
        
        return "\n".join(css_lines)
        
    def list_available_brands(self) -> List[str]:
        """
        List all available brand configurations.
        
        Returns:
            List of brand names (directory names with brand_config.yaml)
        """
        if not self.brands_root.exists():
            return []
            
        brands = []
        for brand_dir in self.brands_root.iterdir():
            if brand_dir.is_dir():
                config_path = brand_dir / "brand_config.yaml"
                if config_path.exists():
                    brands.append(brand_dir.name)
                    
        return sorted(brands)
        
    def create_brand(self, brand_name: str, config: Optional[Dict[str, Any]] = None, 
                    template_name: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None,
                    copy_from: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new brand configuration.
        
        Args:
            brand_name: Name for the new brand (must be valid directory name)
            config: Custom brand configuration dict
            template_name: Name of template to base brand on
            overrides: Specific overrides to apply to template
            copy_from: Name of existing brand to copy from (including assets)
            
        Returns:
            Dict with creation result details
            
        Raises:
            BrandExistsError: If brand already exists
            BrandValidationError: If brand name or config is invalid
            BrandNotFoundError: If copy_from brand doesn't exist
        """
        # Validate brand name
        if not self._is_valid_brand_name(brand_name):
            raise BrandValidationError(f"Invalid brand name: {brand_name}")
            
        brand_path = self.brands_root / brand_name
        if brand_path.exists():
            raise BrandExistsError(f"Brand '{brand_name}' already exists")
            
        try:
            # Create brand directory structure
            brand_path.mkdir(parents=True, exist_ok=True)
            (brand_path / "assets" / "images").mkdir(parents=True, exist_ok=True)
            (brand_path / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
            (brand_path / "templates").mkdir(parents=True, exist_ok=True)
            (brand_path / "backups").mkdir(parents=True, exist_ok=True)
            
            # Determine configuration source
            brand_config = {}
            template_used = None
            
            if copy_from:
                # Copy from existing brand
                source_brand_path = self.brands_root / copy_from
                if not source_brand_path.exists():
                    raise BrandNotFoundError(f"Source brand '{copy_from}' not found")
                
                # Load source brand configuration
                source_config_path = source_brand_path / "brand_config.yaml"
                if source_config_path.exists():
                    with open(source_config_path, 'r', encoding='utf-8') as f:
                        brand_config = yaml.safe_load(f)
                    template_used = copy_from
                
                # Copy assets directory
                source_assets = source_brand_path / "assets"
                if source_assets.exists():
                    shutil.copytree(source_assets, brand_path / "assets", dirs_exist_ok=True)
                
                # Copy templates directory  
                source_templates = source_brand_path / "templates"
                if source_templates.exists():
                    shutil.copytree(source_templates, brand_path / "templates", dirs_exist_ok=True)
                
                logger.info(f"Copied brand structure from '{copy_from}' to '{brand_name}'")
                
            elif template_name:
                # Load from template
                template_config = self._load_template(template_name)
                brand_config = template_config.copy()
                template_used = template_name
                
            if config:
                # Use provided config or merge with template/copy
                if copy_from or template_name:
                    brand_config = self._merge_configs(brand_config, config)
                else:
                    brand_config = config
                    
            if overrides:
                # Apply specific overrides
                brand_config = self._merge_configs(brand_config, overrides)
                
            # Set metadata
            now = datetime.now()
            brand_config.setdefault('metadata', {})
            brand_config['metadata'].update({
                'created_at': now.isoformat(),
                'updated_at': now.isoformat(),
                'version': '1.0.0',
                'status': 'active',
                'template_source': template_used
            })
            
            # Ensure brand section exists and update name
            if 'brand' not in brand_config:
                brand_config['brand'] = {}
            
            # Always update the brand name for new brand
            brand_config['brand']['name'] = brand_name.replace('_', ' ').title()
            
            # Remove protection settings when copying (new brand should not inherit protection)
            if copy_from:
                brand_config.pop('is_protected', None)
                brand_config.pop('protection_level', None)
                brand_config.pop('protected_by', None)
                brand_config.pop('protected_at', None)
                brand_config.pop('protection_reason', None)
                
            # Save configuration
            config_path = brand_path / "brand_config.yaml"
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(brand_config, f, default_flow_style=False, sort_keys=False)
                
            # Get list of created files
            created_files = []
            for item in brand_path.rglob("*"):
                if item.is_file():
                    created_files.append(str(item.relative_to(brand_path)))
                elif item.is_dir():
                    created_files.append(str(item.relative_to(brand_path)) + "/")
                    
            logger.info(f"Successfully created brand: {brand_name}")
            
            return {
                'success': True,
                'brand_name': brand_name,
                'brand_path': str(brand_path),
                'template_used': template_used,
                'created_files': created_files,
                'validation_warnings': [],
                'message': f"Brand '{brand_name}' created successfully."
            }
            
        except Exception as e:
            # Clean up on failure
            if brand_path.exists():
                shutil.rmtree(brand_path)
            logger.error(f"Failed to create brand {brand_name}: {e}")
            raise BrandManagerError(f"Failed to create brand: {e}")
            
    def update_brand(self, brand_name: str, updates: Dict[str, Any], 
                    create_backup: bool = True, force: bool = False) -> Dict[str, Any]:
        """
        Update an existing brand configuration.
        
        Args:
            brand_name: Name of brand to update
            updates: Dictionary of updates to apply
            create_backup: Whether to create backup before updating
            force: Whether to bypass protection checks (admin only)
            
        Returns:
            Dict with update result details
            
        Raises:
            BrandNotFoundError: If brand doesn't exist
            BrandValidationError: If updates are invalid
            BrandProtectionError: If brand is protected and force=False
        """
        brand_path = self.brands_root / brand_name
        config_path = brand_path / "brand_config.yaml"
        
        if not config_path.exists():
            raise BrandNotFoundError(f"Brand '{brand_name}' not found")
            
        # Check protection before proceeding
        if not force:
            self._check_protection(brand_name, "update")
            
        try:
            # Load current configuration
            with open(config_path, 'r', encoding='utf-8') as f:
                current_config = yaml.safe_load(f)
                
            backup_path = None
            if create_backup:
                # Create backup
                backup_path = self._create_backup(brand_name, current_config)
                
            # Apply updates
            updated_config = self._merge_configs(current_config, updates)
            
            # Update metadata
            updated_config.setdefault('metadata', {})
            updated_config['metadata']['updated_at'] = datetime.now().isoformat()
            
            # Increment version if major changes
            if self._has_major_changes(updates):
                version = updated_config['metadata'].get('version', '1.0.0')
                updated_config['metadata']['version'] = self._increment_version(version)
                
            # Validate updated configuration
            validation_warnings = self._validate_config_structure(updated_config)
            
            # Save updated configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(updated_config, f, default_flow_style=False, sort_keys=False)
                
            logger.info(f"Successfully updated brand: {brand_name}")
            
            return {
                'success': True,
                'brand_name': brand_name,
                'backup_path': str(backup_path) if backup_path else None,
                'updated_fields': list(updates.keys()),
                'validation_warnings': validation_warnings,
                'version': updated_config['metadata']['version'],
                'message': f"Brand '{brand_name}' updated successfully."
            }
            
        except Exception as e:
            logger.error(f"Failed to update brand {brand_name}: {e}")
            raise BrandManagerError(f"Failed to update brand: {e}")
            
    def delete_brand(self, brand_name: str, confirm: bool = False, force: bool = False,
                    create_backup: bool = True) -> Dict[str, Any]:
        """
        Delete a brand configuration with safety checks.
        
        Args:
            brand_name: Name of brand to delete
            confirm: Explicit confirmation required
            force: Bypass safety checks and protection
            create_backup: Create backup before deletion
            
        Returns:
            Dict with deletion result details
            
        Raises:
            BrandNotFoundError: If brand doesn't exist
            ValueError: If confirmation not provided and not forced
            BrandProtectionError: If brand is protected and force=False
        """
        if not confirm and not force:
            raise ValueError("Confirmation required for brand deletion")
            
        brand_path = self.brands_root / brand_name
        if not brand_path.exists():
            raise BrandNotFoundError(f"Brand '{brand_name}' not found")
            
        # Check protection before proceeding
        if not force:
            self._check_protection(brand_name, "delete")
            
        try:
            # Get file information before deletion
            deleted_files = []
            total_size = 0
            for item in brand_path.rglob("*"):
                if item.is_file():
                    deleted_files.append(str(item))
                    total_size += item.stat().st_size
                    
            backup_path = None
            if create_backup and not force:
                # Create deletion backup
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.brands_root.parent / f"{brand_name}_deleted_{timestamp}.tar.gz"
                
                with tarfile.open(backup_path, "w:gz") as tar:
                    tar.add(brand_path, arcname=brand_name)
                    
            # Perform deletion
            shutil.rmtree(brand_path)
            
            logger.info(f"Successfully deleted brand: {brand_name}")
            
            return {
                'success': True,
                'brand_name': brand_name,
                'backup_path': str(backup_path) if backup_path else None,
                'deleted_files': deleted_files,
                'force_used': force,
                'safety_checks_bypassed': force,
                'backup_created': backup_path is not None,
                'cleanup_summary': {
                    'files_deleted': len(deleted_files),
                    'directories_removed': len([d for d in brand_path.rglob("*") if d.is_dir()]),
                    'total_size_deleted': total_size
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to delete brand {brand_name}: {e}")
            raise BrandManagerError(f"Failed to delete brand: {e}")
            
    def list_brands_detailed(self, include_metadata: bool = True, 
                           status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        List all brands with enhanced metadata.
        
        Args:
            include_metadata: Include detailed metadata for each brand
            status_filter: Filter by status ('active', 'archived', etc.)
            
        Returns:
            Dict with brands list and metadata
        """
        try:
            brands_list = []
            
            for brand_dir in self.brands_root.iterdir():
                if not brand_dir.is_dir():
                    continue
                    
                config_path = brand_dir / "brand_config.yaml"
                if not config_path.exists():
                    continue
                    
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        
                    metadata = config.get('metadata', {})
                    status = metadata.get('status', 'active')
                    
                    if status_filter and status != status_filter:
                        continue
                        
                    brand_info = {
                        'name': brand_dir.name,
                        'display_name': config.get('brand', {}).get('name', brand_dir.name),
                        'status': status
                    }
                    
                    if include_metadata:
                        # Calculate asset statistics
                        assets_dir = brand_dir / "assets"
                        total_assets = 0
                        total_size = 0
                        
                        if assets_dir.exists():
                            for asset in assets_dir.rglob("*"):
                                if asset.is_file():
                                    total_assets += 1
                                    total_size += asset.stat().st_size
                                    
                        brand_info.update({
                            'template_source': metadata.get('template_source'),
                            'created_at': metadata.get('created_at'),
                            'updated_at': metadata.get('updated_at'),
                            'version': metadata.get('version', '1.0.0'),
                            'total_assets': total_assets,
                            'total_size': total_size,
                            'compliance_status': 'unknown'  # Would run validation
                        })
                        
                    brands_list.append(brand_info)
                    
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {brand_dir.name}: {e}")
                    continue
                    
            # Sort by name
            brands_list.sort(key=lambda x: x['name'])
            
            return {
                'success': True,
                'brands': brands_list,
                'total_count': len(brands_list),
                'status_filter': status_filter,
                'available_statuses': list(set(b.get('status', 'active') for b in brands_list))
            }
            
        except Exception as e:
            logger.error(f"Failed to list brands: {e}")
            raise BrandManagerError(f"Failed to list brands: {e}")
    
    def _is_valid_brand_name(self, name: str) -> bool:
        """Validate brand name for directory/file safety."""
        if not name or len(name) > 50:
            return False
        if not name.replace('_', '').replace('-', '').isalnum():
            return False
        if name.startswith(('.', '_')) or name[0].isdigit():
            return False
        return True
        
    def _load_template(self, template_name: str) -> Dict[str, Any]:
        """Load template configuration."""
        template_path = self.templates_root / template_name / "template_config.yaml"
        if not template_path.exists():
            raise BrandValidationError(f"Template '{template_name}' not found")
            
        with open(template_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
            
    def _merge_configs(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def _create_backup(self, brand_name: str, config: Dict[str, Any]) -> Path:
        """Create backup of current brand configuration."""
        brand_path = self.brands_root / brand_name
        backups_dir = brand_path / "backups"
        backups_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backups_dir / f"backup_{timestamp}.yaml"
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
        return backup_path
        
    def _has_major_changes(self, updates: Dict[str, Any]) -> bool:
        """Determine if updates constitute major changes requiring version bump."""
        major_change_keys = ['colors', 'typography', 'assets', 'compliance']
        return any(key in updates for key in major_change_keys)
        
    def _increment_version(self, version: str) -> str:
        """Increment semantic version string."""
        try:
            parts = version.split('.')
            minor = int(parts[1]) + 1
            return f"{parts[0]}.{minor}.0"
        except (IndexError, ValueError):
            return "1.1.0"
            
    def _validate_config_structure(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration structure and return warnings."""
        warnings = []
        
        required_sections = ['brand', 'colors']
        for section in required_sections:
            if section not in config:
                warnings.append(f"Missing required section: {section}")
                
        return warnings

    def validate_brand_compliance(self, brand_config: BrandConfig) -> List[str]:
        """
        Validate brand configuration against compliance rules.
        
        Args:
            brand_config: BrandConfig object to validate
            
        Returns:
            List of compliance warnings/errors
        """
        warnings = []
        compliance = brand_config.compliance
        
        if not compliance:
            return warnings
            
        # Check required colors
        required_colors = compliance.get('required_colors', [])
        for color in required_colors:
            if color not in brand_config.colors:
                warnings.append(f"Missing required color: {color}")
                
        # Check required fonts
        required_fonts = compliance.get('required_fonts', [])
        primary_font = brand_config.typography.get('primary_font', '')
        secondary_font = brand_config.typography.get('secondary_font', '')
        available_fonts = [primary_font, secondary_font]
        
        for font in required_fonts:
            if font not in available_fonts:
                warnings.append(f"Missing required font: {font}")
                
        # Check color variation limits
        max_variations = compliance.get('max_color_variations', float('inf'))
        if len(brand_config.colors) > max_variations:
            warnings.append(f"Too many color variations: {len(brand_config.colors)} > {max_variations}")
            
        return warnings
    
    def _check_protection(self, brand_name: str, operation: str) -> None:
        """
        Check if a brand is protected against the specified operation.
        
        Args:
            brand_name: Name of the brand to check
            operation: Operation being attempted ("update", "delete", "asset_upload", etc.)
            
        Raises:
            BrandProtectionError: If brand is protected and operation is not allowed
        """
        try:
            config = self.load_brand(brand_name)
            
            # Check if brand is protected
            if not config.is_protected:
                return  # Not protected, allow operation
                
            protection_level = config.protection_level
            protected_reason = config.protection_reason or "Brand is marked as protected"
            
            if protection_level == "strict":
                # Strict protection - block all modifications
                raise BrandProtectionError(
                    f"Cannot {operation} protected brand '{brand_name}': {protected_reason}. "
                    f"Protected by: {config.protected_by or 'system'} on {config.protected_at or 'unknown date'}. "
                    "Use force=True to override (admin only)."
                )
            elif protection_level == "warn":
                # Warning protection - log but allow
                logger.warning(
                    f"Attempting to {operation} protected brand '{brand_name}': {protected_reason}. "
                    f"Protected by: {config.protected_by or 'system'}"
                )
            # "none" protection level allows all operations
                
        except BrandNotFoundError:
            # Brand doesn't exist, no protection to check
            return
        except Exception as e:
            logger.error(f"Error checking protection for brand '{brand_name}': {e}")
            # If we can't check protection, err on the side of caution
            raise BrandProtectionError(
                f"Unable to verify protection status for brand '{brand_name}'. "
                "Protection check failed - operation blocked for safety."
            )
    
    def lock_brand(self, brand_name: str, protection_level: str = "strict", 
                   reason: str = "", protected_by: str = "system") -> Dict[str, Any]:
        """
        Lock a brand to prevent modifications.
        
        Args:
            brand_name: Name of brand to protect
            protection_level: Level of protection ("strict", "warn", "none")
            reason: Reason for protection
            protected_by: Who is applying the protection
            
        Returns:
            Dict with protection result details
            
        Raises:
            BrandNotFoundError: If brand doesn't exist
        """
        if protection_level not in ["strict", "warn", "none"]:
            raise ValueError("Protection level must be 'strict', 'warn', or 'none'")
            
        # Update brand config with protection settings
        protection_updates = {
            "is_protected": protection_level != "none",
            "protection_level": protection_level,
            "protected_by": protected_by,
            "protected_at": datetime.now().isoformat(),
            "protection_reason": reason or f"Brand locked at {protection_level} level"
        }
        
        # Use force=True to bypass existing protection for the lock operation
        result = self.update_brand(brand_name, protection_updates, force=True)
        
        logger.info(f"Brand '{brand_name}' protection set to '{protection_level}' by {protected_by}")
        
        return {
            'success': True,
            'brand_name': brand_name,
            'protection_level': protection_level,
            'protected_by': protected_by,
            'protected_at': protection_updates["protected_at"],
            'reason': protection_updates["protection_reason"],
            'message': f"Brand '{brand_name}' protection set to '{protection_level}'"
        }
    
    def unlock_brand(self, brand_name: str, unlocked_by: str = "system") -> Dict[str, Any]:
        """
        Remove protection from a brand.
        
        Args:
            brand_name: Name of brand to unprotect
            unlocked_by: Who is removing the protection
            
        Returns:
            Dict with unlock result details
            
        Raises:
            BrandNotFoundError: If brand doesn't exist
        """
        # Update brand config to remove protection
        unlock_updates = {
            "is_protected": False,
            "protection_level": "none",
            "protected_by": None,
            "protected_at": None,
            "protection_reason": ""
        }
        
        # Use force=True to bypass existing protection for the unlock operation
        result = self.update_brand(brand_name, unlock_updates, force=True)
        
        logger.info(f"Brand '{brand_name}' protection removed by {unlocked_by}")
        
        return {
            'success': True,
            'brand_name': brand_name,
            'unlocked_by': unlocked_by,
            'unlocked_at': datetime.now().isoformat(),
            'message': f"Brand '{brand_name}' protection removed"
        }
    
    def check_brand_protection(self, brand_name: str) -> Dict[str, Any]:
        """
        Check the protection status of a brand.
        
        Args:
            brand_name: Name of brand to check
            
        Returns:
            Dict with protection status details
            
        Raises:
            BrandNotFoundError: If brand doesn't exist
        """
        config = self.load_brand(brand_name)
        
        return {
            'success': True,
            'brand_name': brand_name,
            'is_protected': config.is_protected,
            'protection_level': config.protection_level,
            'protected_by': config.protected_by,
            'protected_at': config.protected_at.isoformat() if config.protected_at else None,
            'protection_reason': config.protection_reason,
            'can_update': not config.is_protected or config.protection_level != "strict",
            'can_delete': not config.is_protected or config.protection_level != "strict",
            'message': f"Brand '{brand_name}' protection status retrieved"
        }


class AssetManager:
    """
    Manages brand assets including upload, validation, and organization.
    
    Features:
    - Asset upload with Base64 encoding
    - File integrity checking with checksums
    - Asset metadata tracking
    - Automatic cleanup and organization
    - Security validation for file types
    """
    
    ALLOWED_IMAGE_TYPES = {'.png', '.jpg', '.jpeg', '.svg', '.gif'}
    ALLOWED_FONT_TYPES = {'.woff', '.woff2', '.ttf', '.otf', '.eot'}
    ALLOWED_OTHER_TYPES = {'.css', '.js', '.html'}
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, brand_manager: BrandManager):
        """
        Initialize AssetManager.
        
        Args:
            brand_manager: BrandManager instance for accessing brand paths
        """
        self.brand_manager = brand_manager
        
    def upload_asset(self, brand_name: str, asset_data: str, filename: str, 
                    asset_type: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Upload an asset to a brand directory.
        
        Args:
            brand_name: Name of target brand
            asset_data: Base64 encoded file data
            filename: Original filename
            asset_type: Type of asset ('logo', 'font', 'css', etc.)
            metadata: Additional metadata for the asset
            
        Returns:
            Dict with upload result details
            
        Raises:
            BrandNotFoundError: If brand doesn't exist
            BrandValidationError: If asset is invalid
        """
        brand_path = self.brand_manager.brands_root / brand_name
        if not brand_path.exists():
            raise BrandNotFoundError(f"Brand '{brand_name}' not found")
            
        try:
            # Validate base64 data format first
            if not asset_data or not isinstance(asset_data, str):
                raise BrandValidationError("Invalid asset data: must be non-empty base64 string")
                
            # Check for reasonable base64 string length (prevent excessive memory usage)
            if len(asset_data) > self.MAX_FILE_SIZE * 2:  # Base64 is ~1.33x larger
                raise BrandValidationError(f"Base64 data too large: {len(asset_data)} chars")
                
            # Decode and validate asset data with error handling
            try:
                file_data = base64.b64decode(asset_data, validate=True)
            except Exception as e:
                raise BrandValidationError(f"Invalid base64 data: {str(e)}")
            
            # Validate decoded file size
            if len(file_data) > self.MAX_FILE_SIZE:
                raise BrandValidationError(f"File too large: {len(file_data)} bytes > {self.MAX_FILE_SIZE}")
                
            # Validate minimum file size (prevent empty files)
            if len(file_data) == 0:
                raise BrandValidationError("File cannot be empty")
                
            # Validate filename
            if not filename or len(filename) > 255:
                raise BrandValidationError("Invalid filename: must be 1-255 characters")
                
            # Validate file type
            file_ext = Path(filename).suffix.lower()
            if not self._is_allowed_file_type(file_ext):
                raise BrandValidationError(f"File type not allowed: {file_ext}")
                
            # Determine target directory
            target_dir = self._get_asset_directory(brand_path, asset_type)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename if needed
            target_path = target_dir / filename
            if target_path.exists():
                filename = self._generate_unique_filename(target_dir, filename)
                target_path = target_dir / filename
                
            # Calculate checksum
            checksum = hashlib.sha256(file_data).hexdigest()
            
            # Write file
            with open(target_path, 'wb') as f:
                f.write(file_data)
                
            # Create asset metadata
            asset_record = BrandAsset(
                path=target_path,
                asset_type=asset_type,
                file_size=len(file_data),
                checksum=checksum,
                uploaded_at=datetime.now(),
                metadata=metadata or {}
            )
            
            # Update brand asset registry
            self._register_asset(brand_name, filename, asset_record)
            
            logger.info(f"Successfully uploaded asset {filename} to brand {brand_name}")
            
            return {
                'success': True,
                'brand_name': brand_name,
                'filename': filename,
                'asset_type': asset_type,
                'file_path': str(target_path.relative_to(brand_path)),
                'file_size': len(file_data),
                'checksum': checksum,
                'upload_timestamp': asset_record.uploaded_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to upload asset {filename} to brand {brand_name}: {e}")
            raise BrandManagerError(f"Failed to upload asset: {e}")
            
    def validate_asset(self, brand_name: str, asset_path: str) -> Dict[str, Any]:
        """
        Validate an existing asset's integrity and metadata.
        
        Args:
            brand_name: Name of brand containing the asset
            asset_path: Relative path to asset within brand directory
            
        Returns:
            Dict with validation result details
        """
        brand_path = self.brand_manager.brands_root / brand_name
        full_asset_path = brand_path / asset_path
        
        if not full_asset_path.exists():
            return {
                'success': False,
                'asset_path': asset_path,
                'status': 'missing',
                'message': 'Asset file not found'
            }
            
        try:
            # Check file integrity
            with open(full_asset_path, 'rb') as f:
                file_data = f.read()
                
            checksum = hashlib.sha256(file_data).hexdigest()
            file_size = len(file_data)
            
            # Get file stats
            stat = full_asset_path.stat()
            
            # Validate file type
            file_ext = full_asset_path.suffix.lower()
            is_allowed_type = self._is_allowed_file_type(file_ext)
            
            return {
                'success': True,
                'asset_path': asset_path,
                'status': 'valid' if is_allowed_type else 'invalid_type',
                'file_size': file_size,
                'checksum': checksum,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'is_allowed_type': is_allowed_type,
                'file_extension': file_ext,
                'message': 'Asset validation completed'
            }
            
        except Exception as e:
            logger.error(f"Failed to validate asset {asset_path}: {e}")
            return {
                'success': False,
                'asset_path': asset_path,
                'status': 'error',
                'message': f'Validation failed: {e}'
            }
            
    def list_assets(self, brand_name: str, asset_type: Optional[str] = None) -> Dict[str, Any]:
        """
        List all assets for a brand with metadata.
        
        Args:
            brand_name: Name of brand
            asset_type: Filter by asset type (optional)
            
        Returns:
            Dict with assets list and metadata
        """
        brand_path = self.brand_manager.brands_root / brand_name
        if not brand_path.exists():
            raise BrandNotFoundError(f"Brand '{brand_name}' not found")
            
        assets_dir = brand_path / "assets"
        if not assets_dir.exists():
            return {
                'success': True,
                'brand_name': brand_name,
                'assets': [],
                'total_count': 0,
                'total_size': 0
            }
            
        try:
            assets_list = []
            total_size = 0
            
            for asset_path in assets_dir.rglob("*"):
                if asset_path.is_file():
                    # Determine asset type from directory structure
                    relative_path = asset_path.relative_to(assets_dir)
                    inferred_type = self._infer_asset_type(relative_path)
                    
                    # Filter by asset type if specified
                    if asset_type and inferred_type != asset_type:
                        continue
                        
                    # Get file stats
                    stat = asset_path.stat()
                    file_size = stat.st_size
                    total_size += file_size
                    
                    assets_list.append({
                        'filename': asset_path.name,
                        'relative_path': str(relative_path),
                        'asset_type': inferred_type,
                        'file_size': file_size,
                        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'file_extension': asset_path.suffix.lower()
                    })
                    
            # Sort by filename
            assets_list.sort(key=lambda x: x['filename'])
            
            return {
                'success': True,
                'brand_name': brand_name,
                'assets': assets_list,
                'total_count': len(assets_list),
                'total_size': total_size,
                'asset_type_filter': asset_type
            }
            
        except Exception as e:
            logger.error(f"Failed to list assets for brand {brand_name}: {e}")
            raise BrandManagerError(f"Failed to list assets: {e}")
            
    def delete_asset(self, brand_name: str, asset_path: str, 
                    create_backup: bool = True) -> Dict[str, Any]:
        """
        Delete an asset with optional backup.
        
        Args:
            brand_name: Name of brand containing the asset
            asset_path: Relative path to asset within brand directory
            create_backup: Whether to create backup before deletion
            
        Returns:
            Dict with deletion result details
        """
        brand_path = self.brand_manager.brands_root / brand_name
        full_asset_path = brand_path / asset_path
        
        if not full_asset_path.exists():
            raise BrandValidationError(f"Asset not found: {asset_path}")
            
        try:
            # Get file info before deletion
            stat = full_asset_path.stat()
            file_size = stat.st_size
            
            backup_path = None
            if create_backup:
                # Create backup
                backups_dir = brand_path / "backups"
                backups_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{full_asset_path.stem}_{timestamp}{full_asset_path.suffix}"
                backup_path = backups_dir / backup_filename
                
                shutil.copy2(full_asset_path, backup_path)
                
            # Delete the asset
            full_asset_path.unlink()
            
            # Update asset registry
            self._unregister_asset(brand_name, asset_path)
            
            logger.info(f"Successfully deleted asset {asset_path} from brand {brand_name}")
            
            return {
                'success': True,
                'brand_name': brand_name,
                'asset_path': asset_path,
                'backup_path': str(backup_path.relative_to(brand_path)) if backup_path else None,
                'file_size_deleted': file_size,
                'backup_created': backup_path is not None
            }
            
        except Exception as e:
            logger.error(f"Failed to delete asset {asset_path}: {e}")
            raise BrandManagerError(f"Failed to delete asset: {e}")
            
    def cleanup_assets(self, brand_name: str, 
                      remove_unused: bool = False) -> Dict[str, Any]:
        """
        Clean up assets directory, optionally removing unused assets.
        
        Args:
            brand_name: Name of brand to clean up
            remove_unused: Whether to remove assets not referenced in config
            
        Returns:
            Dict with cleanup result details
        """
        brand_path = self.brand_manager.brands_root / brand_name
        if not brand_path.exists():
            raise BrandNotFoundError(f"Brand '{brand_name}' not found")
            
        try:
            cleanup_summary = {
                'files_processed': 0,
                'files_removed': 0,
                'space_reclaimed': 0,
                'empty_dirs_removed': 0
            }
            
            assets_dir = brand_path / "assets"
            if not assets_dir.exists():
                return {
                    'success': True,
                    'brand_name': brand_name,
                    'cleanup_summary': cleanup_summary,
                    'message': 'No assets directory to clean'
                }
                
            # Get referenced assets if removing unused
            referenced_assets = set()
            if remove_unused:
                try:
                    brand_config = self.brand_manager.load_brand(brand_name)
                    referenced_assets = self._extract_referenced_assets(brand_config)
                except Exception as e:
                    logger.warning(f"Could not load brand config for cleanup: {e}")
                    
            # Process all files
            for asset_path in list(assets_dir.rglob("*")):
                if asset_path.is_file():
                    cleanup_summary['files_processed'] += 1
                    
                    # Check if file should be removed
                    should_remove = False
                    relative_path = asset_path.relative_to(assets_dir)
                    
                    if remove_unused and str(relative_path) not in referenced_assets:
                        should_remove = True
                        
                    if should_remove:
                        file_size = asset_path.stat().st_size
                        asset_path.unlink()
                        cleanup_summary['files_removed'] += 1
                        cleanup_summary['space_reclaimed'] += file_size
                        
            # Remove empty directories
            for dir_path in list(assets_dir.rglob("*")):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    cleanup_summary['empty_dirs_removed'] += 1
                    
            logger.info(f"Cleaned up assets for brand {brand_name}")
            
            return {
                'success': True,
                'brand_name': brand_name,
                'cleanup_summary': cleanup_summary,
                'message': f"Cleanup completed. Removed {cleanup_summary['files_removed']} files."
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup assets for brand {brand_name}: {e}")
            raise BrandManagerError(f"Failed to cleanup assets: {e}")
    
    def _is_allowed_file_type(self, file_ext: str) -> bool:
        """Check if file extension is allowed."""
        return file_ext in (self.ALLOWED_IMAGE_TYPES | self.ALLOWED_FONT_TYPES | self.ALLOWED_OTHER_TYPES)
        
    def _get_asset_directory(self, brand_path: Path, asset_type: str) -> Path:
        """Get the appropriate subdirectory for an asset type."""
        asset_dirs = {
            'logo': 'assets/images',
            'image': 'assets/images',
            'font': 'assets/fonts',
            'css': 'assets',
            'template': 'templates'
        }
        
        subdir = asset_dirs.get(asset_type, 'assets/misc')
        return brand_path / subdir
        
    def _generate_unique_filename(self, directory: Path, filename: str) -> str:
        """Generate a unique filename if the original already exists."""
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        
        while (directory / filename).exists():
            filename = f"{stem}_{counter}{suffix}"
            counter += 1
            
        return filename
        
    def _infer_asset_type(self, relative_path: Path) -> str:
        """Infer asset type from its relative path within assets directory."""
        parts = relative_path.parts
        
        if 'images' in parts:
            return 'image'
        elif 'fonts' in parts:
            return 'font'
        elif relative_path.suffix.lower() == '.css':
            return 'css'
        else:
            return 'misc'
            
    def _register_asset(self, brand_name: str, filename: str, asset_record: BrandAsset) -> None:
        """Register asset in the brand's asset registry."""
        # This would update a registry file or database in a full implementation
        # For now, we'll use a simple JSON file approach
        brand_path = self.brand_manager.brands_root / brand_name
        registry_path = brand_path / "asset_registry.json"
        
        try:
            if registry_path.exists():
                with open(registry_path, 'r') as f:
                    registry = json.load(f)
            else:
                registry = {}
                
            registry[filename] = {
                'asset_type': asset_record.asset_type,
                'file_size': asset_record.file_size,
                'checksum': asset_record.checksum,
                'uploaded_at': asset_record.uploaded_at.isoformat(),
                'metadata': asset_record.metadata
            }
            
            with open(registry_path, 'w') as f:
                json.dump(registry, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to update asset registry: {e}")
            
    def _unregister_asset(self, brand_name: str, asset_path: str) -> None:
        """Remove asset from the brand's asset registry."""
        brand_path = self.brand_manager.brands_root / brand_name
        registry_path = brand_path / "asset_registry.json"
        
        try:
            if not registry_path.exists():
                return
                
            with open(registry_path, 'r') as f:
                registry = json.load(f)
                
            filename = Path(asset_path).name
            if filename in registry:
                del registry[filename]
                
                with open(registry_path, 'w') as f:
                    json.dump(registry, f, indent=2)
                    
        except Exception as e:
            logger.warning(f"Failed to update asset registry: {e}")
            
    def _extract_referenced_assets(self, brand_config: BrandConfig) -> set:
        """Extract all asset paths referenced in brand configuration."""
        referenced = set()
        
        # Extract from assets section
        for asset_path in brand_config.assets.values():
            if isinstance(asset_path, list):
                referenced.update(asset_path)
            else:
                referenced.add(asset_path)
                
        # Extract from templates if they reference assets
        # This could be expanded based on template structure
        
        return referenced


class BrandTemplateManager:
    """
    Manages brand templates for consistent brand creation.
    
    Features:
    - Template creation and validation
    - Template categorization and organization
    - Template inheritance and customization
    - Template versioning and metadata
    """
    
    def __init__(self, brand_manager: BrandManager):
        """
        Initialize BrandTemplateManager.
        
        Args:
            brand_manager: BrandManager instance for accessing template paths
        """
        self.brand_manager = brand_manager
        self.templates_root = brand_manager.templates_root
        
    def create_template(self, template_name: str, template_config: Dict[str, Any],
                       description: str, category: str = "custom",
                       features: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a new brand template.
        
        Args:
            template_name: Name for the template
            template_config: Template configuration dictionary
            description: Description of the template
            category: Template category
            features: List of template features
            
        Returns:
            Dict with creation result details
        """
        if not self._is_valid_template_name(template_name):
            raise BrandValidationError(f"Invalid template name: {template_name}")
            
        template_path = self.templates_root / template_name
        if template_path.exists():
            raise BrandExistsError(f"Template '{template_name}' already exists")
            
        try:
            # Create template directory
            template_path.mkdir(parents=True, exist_ok=True)
            
            # Add template metadata
            template_config.setdefault('template_info', {})
            template_config['template_info'].update({
                'name': template_name,
                'description': description,
                'category': category,
                'version': '1.0.0',
                'created_at': datetime.now().isoformat(),
                'features': features or [],
                'required_assets': self._extract_required_assets(template_config),
                'optional_assets': self._extract_optional_assets(template_config)
            })
            
            # Validate template configuration
            validation_warnings = self._validate_template_config(template_config)
            
            # Save template configuration
            config_path = template_path / "template_config.yaml"
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(template_config, f, default_flow_style=False, sort_keys=False)
                
            # Create template assets directory if needed
            if template_config.get('assets'):
                assets_dir = template_path / "assets"
                assets_dir.mkdir(exist_ok=True)
                
            logger.info(f"Successfully created template: {template_name}")
            
            return {
                'success': True,
                'template_name': template_name,
                'template_path': str(template_path),
                'category': category,
                'version': template_config['template_info']['version'],
                'validation_warnings': validation_warnings,
                'message': f"Template '{template_name}' created successfully."
            }
            
        except Exception as e:
            # Clean up on failure
            if template_path.exists():
                shutil.rmtree(template_path)
            logger.error(f"Failed to create template {template_name}: {e}")
            raise BrandManagerError(f"Failed to create template: {e}")
            
    def load_template(self, template_name: str) -> BrandTemplate:
        """
        Load a brand template.
        
        Args:
            template_name: Name of template to load
            
        Returns:
            BrandTemplate object with template configuration
        """
        template_path = self.templates_root / template_name
        config_path = template_path / "template_config.yaml"
        
        if not config_path.exists():
            raise BrandNotFoundError(f"Template '{template_name}' not found")
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                template_config = yaml.safe_load(f)
                
            template_info = template_config.get('template_info', {})
            
            return BrandTemplate(
                name=template_info.get('name', template_name),
                description=template_info.get('description', ''),
                category=template_info.get('category', 'custom'),
                version=template_info.get('version', '1.0.0'),
                config=template_config,
                features=template_info.get('features', []),
                required_assets=template_info.get('required_assets', []),
                optional_assets=template_info.get('optional_assets', [])
            )
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in template config {config_path}: {e}")
            raise BrandValidationError(f"Invalid template configuration: {e}")
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            raise BrandValidationError(f"Failed to load template: {e}")
            
    def list_templates(self, category_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        List all available templates with metadata.
        
        Args:
            category_filter: Filter templates by category
            
        Returns:
            Dict with templates list and metadata
        """
        try:
            templates_list = []
            categories = set()
            
            for template_dir in self.templates_root.iterdir():
                if not template_dir.is_dir():
                    continue
                    
                config_path = template_dir / "template_config.yaml"
                if not config_path.exists():
                    continue
                    
                try:
                    template = self.load_template(template_dir.name)
                    categories.add(template.category)
                    
                    if category_filter and template.category != category_filter:
                        continue
                        
                    templates_list.append({
                        'name': template.name,
                        'description': template.description,
                        'category': template.category,
                        'version': template.version,
                        'features': template.features,
                        'required_assets': template.required_assets,
                        'optional_assets': template.optional_assets
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to load template {template_dir.name}: {e}")
                    continue
                    
            # Sort by category, then name
            templates_list.sort(key=lambda x: (x['category'], x['name']))
            
            return {
                'success': True,
                'templates': templates_list,
                'total_count': len(templates_list),
                'categories': sorted(list(categories)),
                'category_filter': category_filter
            }
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            raise BrandManagerError(f"Failed to list templates: {e}")
            
    def update_template(self, template_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing template.
        
        Args:
            template_name: Name of template to update
            updates: Dictionary of updates to apply
            
        Returns:
            Dict with update result details
        """
        template_path = self.templates_root / template_name
        config_path = template_path / "template_config.yaml"
        
        if not config_path.exists():
            raise BrandNotFoundError(f"Template '{template_name}' not found")
            
        try:
            # Load current template
            with open(config_path, 'r', encoding='utf-8') as f:
                current_config = yaml.safe_load(f)
                
            # Apply updates
            updated_config = self.brand_manager._merge_configs(current_config, updates)
            
            # Update template metadata
            updated_config.setdefault('template_info', {})
            template_info = updated_config['template_info']
            template_info['updated_at'] = datetime.now().isoformat()
            
            # Increment version for significant changes
            if self._has_template_changes(updates):
                version = template_info.get('version', '1.0.0')
                template_info['version'] = self.brand_manager._increment_version(version)
                
            # Re-extract asset lists if template changed
            if 'assets' in updates:
                template_info['required_assets'] = self._extract_required_assets(updated_config)
                template_info['optional_assets'] = self._extract_optional_assets(updated_config)
                
            # Validate updated template
            validation_warnings = self._validate_template_config(updated_config)
            
            # Save updated template
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(updated_config, f, default_flow_style=False, sort_keys=False)
                
            logger.info(f"Successfully updated template: {template_name}")
            
            return {
                'success': True,
                'template_name': template_name,
                'updated_fields': list(updates.keys()),
                'validation_warnings': validation_warnings,
                'version': template_info['version'],
                'message': f"Template '{template_name}' updated successfully."
            }
            
        except Exception as e:
            logger.error(f"Failed to update template {template_name}: {e}")
            raise BrandManagerError(f"Failed to update template: {e}")
            
    def delete_template(self, template_name: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a template with confirmation.
        
        Args:
            template_name: Name of template to delete
            confirm: Explicit confirmation required
            
        Returns:
            Dict with deletion result details
        """
        if not confirm:
            raise ValueError("Confirmation required for template deletion")
            
        template_path = self.templates_root / template_name
        if not template_path.exists():
            raise BrandNotFoundError(f"Template '{template_name}' not found")
            
        try:
            # Get template info before deletion
            try:
                template = self.load_template(template_name)
                template_info = {
                    'name': template.name,
                    'category': template.category,
                    'version': template.version
                }
            except:
                template_info = {'name': template_name}
                
            # Delete template directory
            shutil.rmtree(template_path)
            
            logger.info(f"Successfully deleted template: {template_name}")
            
            return {
                'success': True,
                'template_name': template_name,
                'template_info': template_info,
                'message': f"Template '{template_name}' deleted successfully."
            }
            
        except Exception as e:
            logger.error(f"Failed to delete template {template_name}: {e}")
            raise BrandManagerError(f"Failed to delete template: {e}")
            
    def validate_template(self, template_name: str) -> Dict[str, Any]:
        """
        Validate a template configuration.
        
        Args:
            template_name: Name of template to validate
            
        Returns:
            Dict with validation results
        """
        try:
            template = self.load_template(template_name)
            issues = []
            
            # Validate template structure
            structure_issues = self._validate_template_config(template.config)
            issues.extend([{'type': 'structure', 'message': issue} for issue in structure_issues])
            
            # Validate asset references
            asset_issues = self._validate_template_assets(template)
            issues.extend([{'type': 'asset', 'message': issue} for issue in asset_issues])
            
            # Determine overall status
            if not issues:
                status = 'valid'
            elif any(issue['type'] == 'structure' for issue in issues):
                status = 'error'
            else:
                status = 'warning'
                
            return {
                'success': True,
                'template_name': template_name,
                'status': status,
                'issues': issues,
                'message': f"Template validation completed with status: {status}"
            }
            
        except Exception as e:
            logger.error(f"Failed to validate template {template_name}: {e}")
            return {
                'success': False,
                'template_name': template_name,
                'status': 'error',
                'message': f"Validation failed: {e}"
            }
    
    def _is_valid_template_name(self, name: str) -> bool:
        """Validate template name."""
        return self.brand_manager._is_valid_brand_name(name)
        
    def _validate_template_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate template configuration structure."""
        warnings = []
        
        # Check required sections
        required_sections = ['brand', 'colors']
        for section in required_sections:
            if section not in config:
                warnings.append(f"Missing required section: {section}")
                
        # Check template_info section
        if 'template_info' not in config:
            warnings.append("Missing template_info section")
        else:
            template_info = config['template_info']
            required_info = ['name', 'description', 'category']
            for field in required_info:
                if field not in template_info:
                    warnings.append(f"Missing template_info field: {field}")
                    
        return warnings
        
    def _validate_template_assets(self, template: BrandTemplate) -> List[str]:
        """Validate template asset references."""
        issues = []
        
        # Check if required assets are reasonable
        if len(template.required_assets) > 20:
            issues.append("Template requires too many assets (>20)")
            
        # Check for common asset types
        asset_types = set()
        for asset in template.required_assets + template.optional_assets:
            if isinstance(asset, str):
                ext = Path(asset).suffix.lower()
                if ext in {'.png', '.jpg', '.jpeg', '.svg'}:
                    asset_types.add('image')
                elif ext in {'.woff', '.woff2', '.ttf', '.otf'}:
                    asset_types.add('font')
                elif ext == '.css':
                    asset_types.add('css')
                    
        if not asset_types:
            issues.append("Template doesn't specify any standard asset types")
            
        return issues
        
    def _extract_required_assets(self, config: Dict[str, Any]) -> List[str]:
        """Extract required asset paths from template configuration."""
        required = []
        
        # Extract from assets section
        assets = config.get('assets', {})
        for key, value in assets.items():
            if isinstance(value, list):
                required.extend(value)
            elif value:
                required.append(value)
                
        # Extract from compliance rules
        compliance = config.get('compliance', {})
        if 'required_assets' in compliance:
            required.extend(compliance['required_assets'])
            
        return list(set(required))  # Remove duplicates
        
    def _extract_optional_assets(self, config: Dict[str, Any]) -> List[str]:
        """Extract optional asset paths from template configuration."""
        optional = []
        
        # This could be expanded based on specific template structure
        # For now, we'll consider watermarks, additional logos, etc.
        assets = config.get('assets', {})
        optional_keys = ['watermark', 'favicon', 'background']
        
        for key in optional_keys:
            if key in assets and assets[key]:
                if isinstance(assets[key], list):
                    optional.extend(assets[key])
                else:
                    optional.append(assets[key])
                    
        return list(set(optional))
        
    def _has_template_changes(self, updates: Dict[str, Any]) -> bool:
        """Determine if updates warrant version increment."""
        significant_keys = ['brand', 'colors', 'typography', 'assets', 'compliance']
        return any(key in updates for key in significant_keys)