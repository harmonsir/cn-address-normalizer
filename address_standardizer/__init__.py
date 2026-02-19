from pathlib import Path
from typing import Optional, Union

from .base import Region, RegionLevel, RegionWithHierarchy, SearchResult
from .builder import RegionIndexBuilder
from .engine import AddressStandardizer, RegionSearchEngine
from .storage import StorageManager


__all__ = [
    "RegionSearchEngine",
    "AddressStandardizer",
    "RegionIndexBuilder",
    "Region",
    "SearchResult",
    "RegionLevel",
    "RegionWithHierarchy",
    "StorageManager",
    "load_standardizer"
]

__version__ = "1.0.0"  # Promoted to v1 for the new architecture


def load_standardizer(region: str = "cn", index_path: Optional[Union[str, Path]] = None) -> RegionSearchEngine:
    """
    Factory function to load a standardizer for a specific region.
    
    Args:
        region: Region code (default 'cn')
        index_path: Optional custom path to index file. 
                   If not provided, looks in address_standardizer/data/{region}/regions_index.bin
    """
    if index_path:
        return RegionSearchEngine(index_path)

    # Default built-in index discovery
    # We prefer the new regions_index.bin but fallback to old address_standardizer.bin if needed
    pkg_dir = Path(__file__).parent

    search_paths = [
        pkg_dir / "data" / region / "regions_index.bin",
        pkg_dir / "data" / "regions_index.bin",
        pkg_dir / "regions_index.bin",
    ]

    for path in search_paths:
        if path.exists():
            return RegionSearchEngine(path)

    # Try old format for compatibility if StorageManager can handle it (it might fail if format changed too much)
    old_path = pkg_dir / "data" / region / "address_standardizer.bin"
    if old_path.exists():
        try:
            return RegionSearchEngine(old_path)
        except Exception:
            pass

    return RegionSearchEngine()
