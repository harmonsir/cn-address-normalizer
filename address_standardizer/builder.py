import time
from collections import defaultdict
from typing import Any, Dict, List

from .storage import StorageManager
from .utils import BitmapIndex


class RegionIndexBuilder:
    """High-performance index builder for administrative divisions."""

    def __init__(self, regions: List[Dict]):
        """
        Initialize builder with raw region data.
        
        Args:
            regions: List of dicts, each containing:
                - code, name, level, pinyin, pinyin_short, parent_code, full_path
        """
        self.regions = regions
        self.region_count = len(regions)

        # Main indices
        self.code_to_index = {}  # code -> array index
        self.code_to_region = {}  # code -> region dict

        # Inverted indices
        self.name_inverted = defaultdict(set)
        self.pinyin_inverted = defaultdict(set)
        self.short_inverted = defaultdict(set)
        self.level_inverted = defaultdict(set)
        self.parent_inverted = defaultdict(set)

        # Trie indices
        self.name_trie = {}
        self.pinyin_trie = {}
        self.short_trie = {}

        # N-gram indices
        self.name_ngrams = defaultdict(set)
        self.pinyin_ngrams = defaultdict(set)

        # Bitmap indices
        self.bitmap_indices = {}

        # Cache
        self.ancestor_cache = {}

        self.stats = {
            "build_time": 0,
            "region_count": self.region_count,
            "index_counts": {}
        }

    def build_all_indices(self) -> Dict[str, Any]:
        """Execute the full building pipeline."""
        start_time = time.time()

        self._build_basic_indices()
        self._build_inverted_indices()
        self._build_trie_indices()
        self._build_ngram_indices(n=2)
        self._build_ngram_indices(n=3)
        self._build_bitmap_indices()
        self._build_relation_indices()

        self.stats["build_time"] = time.time() - start_time
        self._calculate_stats()

        return self._get_index_structure()

    def _build_basic_indices(self):
        for idx, region in enumerate(self.regions):
            code = region["code"]
            self.code_to_index[code] = idx
            self.code_to_region[code] = region

    def _build_inverted_indices(self):
        for region in self.regions:
            code = region["code"]

            # Full name and characters
            name_lower = region["name"].lower()
            self.name_inverted[name_lower].add(code)
            for char in region["name"]:
                self.name_inverted[char].add(code)

            if region.get("pinyin"):
                pinyin_lower = region["pinyin"].lower()
                pinyin_clean = pinyin_lower.replace(" ", "")
                self.pinyin_inverted[pinyin_lower].add(code)
                self.pinyin_inverted[pinyin_clean].add(code)
                for char in pinyin_clean:
                    self.pinyin_inverted[char].add(code)

            if region.get("pinyin_short"):
                short_lower = region["pinyin_short"].lower()
                self.short_inverted[short_lower].add(code)
                for char in short_lower:
                    self.short_inverted[char].add(code)

            self.level_inverted[region["level"]].add(code)

            if region.get("parent_code"):
                self.parent_inverted[region["parent_code"]].add(code)

    def _build_trie_indices(self):
        for region in self.regions:
            code = region["code"]
            self._add_to_trie(self.name_trie, region["name"], code)

            if region.get("pinyin"):
                pinyin = region["pinyin"].replace(" ", "")
                self._add_to_trie(self.pinyin_trie, pinyin, code)

            if region.get("pinyin_short"):
                self._add_to_trie(self.short_trie, region["pinyin_short"], code)

    def _add_to_trie(self, trie: Dict, text: str, code: str):
        node = trie
        for char in text:
            if char not in node:
                node[char] = {"codes": set()}
            node = node[char]
            if "codes" not in node:
                node["codes"] = set()
            node["codes"].add(code)
        node["$"] = True

    def _build_ngram_indices(self, n: int = 2):
        for region in self.regions:
            code = region["code"]
            name = region["name"]
            for i in range(len(name) - n + 1):
                self.name_ngrams[name[i:i + n]].add(code)

            if region.get("pinyin"):
                pinyin = region["pinyin"].replace(" ", "")
                for i in range(len(pinyin) - n + 1):
                    self.pinyin_ngrams[pinyin[i:i + n]].add(code)

    def _build_bitmap_indices(self):
        for level, codes in self.level_inverted.items():
            bitmap = BitmapIndex(self.region_count)
            for code in codes:
                bitmap.set(self.code_to_index[code])
            self.bitmap_indices[f"level_{level}"] = bitmap

        # Common initials optimization
        common_initials = ["bj", "sh", "gz", "sz", "cd"]
        for initial in common_initials:
            if initial in self.short_inverted:
                bitmap = BitmapIndex(self.region_count)
                for code in self.short_inverted[initial]:
                    bitmap.set(self.code_to_index[code])
                self.bitmap_indices[f"initial_{initial}"] = bitmap

    def _build_relation_indices(self):
        for region in self.regions:
            code = region["code"]
            self.ancestor_cache[code] = self._get_ancestors(code)

    def _get_ancestors(self, code: str) -> List[str]:
        ancestors = []
        current = code
        while current in self.code_to_region:
            region = self.code_to_region[current]
            ancestors.insert(0, current)
            current = region.get("parent_code")
            if not current:
                break
        return ancestors

    def _calculate_stats(self):
        self.stats["index_counts"] = {
            "regions": self.region_count,
            "name_terms": len(self.name_inverted),
            "pinyin_terms": len(self.pinyin_inverted),
            "short_terms": len(self.short_inverted),
            "bitmap_indices": len(self.bitmap_indices),
            "ngram_terms": len(self.name_ngrams) + len(self.pinyin_ngrams)
        }

    def _get_index_structure(self) -> Dict[str, Any]:
        def convert_sets(obj):
            if isinstance(obj, set): return list(obj)
            if isinstance(obj, dict): return {k: convert_sets(v) for k, v in obj.items()}
            if isinstance(obj, list): return [convert_sets(item) for item in obj]
            return obj

        return {
            "code_to_index": self.code_to_index,
            "code_to_region": self.code_to_region,
            "name_inverted": convert_sets(self.name_inverted),
            "pinyin_inverted": convert_sets(self.pinyin_inverted),
            "short_inverted": convert_sets(self.short_inverted),
            "level_inverted": convert_sets(self.level_inverted),
            "parent_inverted": convert_sets(self.parent_inverted),
            "name_trie": convert_sets(self.name_trie),
            "pinyin_trie": convert_sets(self.pinyin_trie),
            "short_trie": convert_sets(self.short_trie),
            "name_ngrams": convert_sets(self.name_ngrams),
            "pinyin_ngrams": convert_sets(self.pinyin_ngrams),
            "ancestor_cache": self.ancestor_cache,
            "bitmap_indices": self.bitmap_indices,  # BitmapIndex is serializable if pickle is used
            "stats": self.stats
        }

    def save_to_file(self, filepath: str):
        """Save the built index using StorageManager."""
        index_data = self._get_index_structure()
        StorageManager.save(filepath, index_data)

    def get_regions_by_level(self, level: str) -> List[Dict]:
        return [self.code_to_region[code] for code in self.level_inverted.get(level, set())]
