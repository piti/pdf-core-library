"""
Storage abstraction layer for pluggable storage backends.
Provides interface for local storage with extensibility for future implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Optional, Dict, Any
import asyncio
import shutil
import logging

logger = logging.getLogger(__name__)

class StorageInterface(ABC):
    """Abstract storage interface for pluggable storage backends"""
    
    @abstractmethod
    async def upload_file(self, file_path: Path, key: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Upload file and return access URL"""
        pass
    
    @abstractmethod
    async def download_file(self, key: str, local_path: Path) -> Path:
        """Download file to local path"""
        pass
    
    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """Delete file by key"""
        pass
    
    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        """Check if file exists"""
        pass

class LocalStorage(StorageInterface):
    """Local filesystem storage implementation"""
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path("./storage")
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    async def upload_file(self, file_path: Path, key: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Upload file to local storage"""
        target_path = self.base_path / key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use asyncio to avoid blocking
        await asyncio.to_thread(shutil.copy2, file_path, target_path)
        
        logger.info(f"File uploaded to local storage: {target_path}")
        return f"file://{target_path.absolute()}"
    
    async def download_file(self, key: str, local_path: Path) -> Path:
        """Download file from local storage"""
        source_path = self.base_path / key
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        
        local_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, source_path, local_path)
        
        return local_path
    
    async def delete_file(self, key: str) -> bool:
        """Delete file from local storage"""
        file_path = self.base_path / key
        if file_path.exists():
            await asyncio.to_thread(file_path.unlink)
            return True
        return False
    
    async def file_exists(self, key: str) -> bool:
        """Check if file exists in local storage"""
        return (self.base_path / key).exists()