from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RegionLevel(Enum):
    """Administrative division levels."""
    PROVINCE = "省级"
    CITY = "市级"
    DISTRICT = "区县级"
    SUBDISTRICT = "街道级"
    VILLAGE = "村级"


@dataclass
class Region:
    """Basic region model."""
    code: str
    name: str
    level: str
    parent_code: str = ""
    parent_name: str = ""
    full_path: str = ""
    pinyin: str = ""
    pinyin_short: str = ""

    # Optional extensions
    short_name: Optional[str] = None
    alias: List[str] = field(default_factory=list)
    lat: Optional[float] = None
    lng: Optional[float] = None

    @property
    def level_rank(self) -> int:
        """Numeric rank for sorting (1 is highest)."""
        level_map = {
            "省级": 1,
            "市级": 2,
            "区县级": 3,
            "街道级": 4,
            "村级": 5
        }
        return level_map.get(self.level, 99)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "level": self.level,
            "parent_code": self.parent_code,
            "parent_name": self.parent_name,
            "full_path": self.full_path,
            "pinyin": self.pinyin,
            "pinyin_short": self.pinyin_short,
            "short_name": self.short_name,
            "alias": self.alias,
            "lat": self.lat,
            "lng": self.lng
        }


@dataclass
class RegionWithHierarchy:
    """Region model with full hierarchy context."""
    current: Region
    hierarchy: Dict[str, Region] = field(default_factory=dict)  # level_name -> Region
    display_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current": self.current.to_dict(),
            "hierarchy": {k: v.to_dict() for k, v in self.hierarchy.items()},
            "display_path": self.display_path
        }


@dataclass
class SearchResult:
    """Container for search results with scoring."""
    region: Region
    full_info: Dict[str, Any]  # Matches the structure expected by the frontend/user
    score: float
    match_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region": self.region.to_dict(),
            "full_info": self.full_info,
            "score": self.score,
            "match_type": self.match_type
        }
