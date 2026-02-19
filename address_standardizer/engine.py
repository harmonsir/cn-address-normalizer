import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from .base import Region, SearchResult
from .storage import StorageManager


logger = logging.getLogger(__name__)

COMMON_SUFFIXES = ["省", "市", "区", "县", "自治州", "自治区", "特别行政区"]


class FuzzySearchAlgorithm:
    """Fuzzy search algorithm implementation."""

    def __init__(self, index_data: Dict[str, Any]):
        self.index = index_data
        self.config = {
            "fuzzy_threshold": 0.7,
            "max_edit_distance": 2,
            "boost_exact_match": 2.0,
            "boost_prefix_match": 1.5,
            "min_ngram_overlap": 0.3,
            "level_weights": {
                "省级": 1.0,
                "市级": 0.8,
                "区县级": 0.6
            }
        }

    def search(self, query: str, limit: int = 10, search_type: str = "all") -> List[SearchResult]:
        query = query.strip().lower()
        if not query:
            return []

        candidates = self._parallel_search(query, search_type)
        if not candidates:
            return []

        scored_results = []
        for code in candidates:
            score = self._calculate_score(code, query)
            region_dict = self.index["code_to_region"][code]
            region = Region(**region_dict)

            full_info = self._build_full_info(code)
            scored_results.append(SearchResult(
                region=region,
                full_info=full_info,
                score=score,
                match_type=self._get_match_type(code, query)
            ))

        scored_results.sort(
            key=lambda x: (x.score, -x.full_info["level_rank"]),
            reverse=True
        )

        return scored_results[:limit]

    def _parallel_search(self, query: str, search_type: str) -> Set[str]:
        candidates = set()

        # Strategy 1: Exact search
        candidates.update(self._exact_search(query, search_type))

        # Strategy 2: Prefix search (Trie)
        candidates.update(self._prefix_search(query, search_type))

        # Strategy 3: N-gram search
        candidates.update(self._ngram_search(query, search_type))

        # Strategy 4: Fuzzy search (Levenshtein) - only if few candidates
        if len(candidates) < 20:
            candidates.update(self._fuzzy_search(query, search_type))

        return candidates

    def _exact_search(self, query: str, search_type: str) -> Set[str]:
        results = set()
        if search_type in ["all", "name"]:
            if query in self.index["name_inverted"]:
                results.update(self.index["name_inverted"][query])
            # Fallback for full name exact match not in inverted index chars
            for code, region in self.index["code_to_region"].items():
                if query == region["name"].lower():
                    results.add(code)

        if search_type in ["all", "pinyin"]:
            if query in self.index["pinyin_inverted"]:
                results.update(self.index["pinyin_inverted"][query])
            for code, region in self.index["code_to_region"].items():
                if region.get("pinyin") and query == region["pinyin"].lower().replace(" ", ""):
                    results.add(code)

        if search_type in ["all", "short"]:
            if query in self.index["short_inverted"]:
                results.update(self.index["short_inverted"][query])

        return results

    def _prefix_search(self, query: str, search_type: str) -> Set[str]:
        results = set()

        def search_trie(trie: Dict, prefix: str) -> Set[str]:
            node = trie
            for char in prefix:
                if char not in node:
                    return set()
                node = node[char]

            codes = set()
            stack = [node]
            while stack:
                current = stack.pop()
                if "codes" in current:
                    codes.update(current["codes"])
                for key, child in current.items():
                    if key not in ["codes", "$"]:
                        stack.append(child)
            return codes

        if search_type in ["all", "name"]:
            results.update(search_trie(self.index["name_trie"], query))
        if search_type in ["all", "pinyin"]:
            results.update(search_trie(self.index["pinyin_trie"], query))
        if search_type in ["all", "short"]:
            results.update(search_trie(self.index["short_trie"], query))

        return results

    def _ngram_search(self, query: str, search_type: str) -> Set[str]:
        results = set()
        ngram_sets = {}
        for n in [2, 3]:
            ngrams = {query[i:i + n] for i in range(len(query) - n + 1)}
            ngram_sets[n] = ngrams

        if search_type in ["all", "name"]:
            for ngrams in ngram_sets.values():
                for ngram in ngrams:
                    if ngram in self.index["name_ngrams"]:
                        results.update(self.index["name_ngrams"][ngram])

        if search_type in ["all", "pinyin"]:
            for ngrams in ngram_sets.values():
                for ngram in ngrams:
                    if ngram in self.index["pinyin_ngrams"]:
                        results.update(self.index["pinyin_ngrams"][ngram])
        return results

    def _fuzzy_search(self, query: str, search_type: str) -> Set[str]:
        results = set()
        max_distance = self.config["max_edit_distance"]
        for code, region in self.index["code_to_region"].items():
            if search_type in ["all", "name"]:
                name = region["name"].lower()
                if self._levenshtein_distance(query, name[:len(query) + max_distance]) <= max_distance:
                    results.add(code)
            if search_type in ["all", "pinyin"] and region.get("pinyin"):
                pinyin = region["pinyin"].lower().replace(" ", "")
                if self._levenshtein_distance(query, pinyin[:len(query) + max_distance]) <= max_distance:
                    results.add(code)
        return results

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2): return self._levenshtein_distance(s2, s1)
        if len(s2) == 0: return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def _calculate_score(self, code: str, query: str) -> float:
        region = self.index["code_to_region"][code]
        score = 0.0

        # 1. Basic match score
        score += self._calculate_basic_match_score(region, query)

        # 2. Position weight
        score += self._calculate_position_score(region, query)

        # 3. Level weight
        level_weight = self.config["level_weights"].get(region["level"], 0.5)
        score *= level_weight

        # 4. Full path reward (more lenient)
        if region.get("full_path"):
            full_path = region["full_path"].lower()
            clean_path = full_path.replace(">", "")
            if query in full_path or query in clean_path:
                path_factor = len(full_path.split(">")) / 3.0
                score += 0.5 * path_factor  # Increased reward
            else:
                # Check if parts of query are in path
                parts_found = 0
                for part in re.findall(r"[\u4e00-\u9fff]+|[a-z]+", query):
                    if part in full_path:
                        parts_found += 1
                if parts_found > 0:
                    score += 0.2 * parts_found

        # 5. Pinyin similarity
        if query.isalpha():
            if region.get("pinyin"):
                pinyin = region["pinyin"].lower().replace(" ", "")
                similarity = SequenceMatcher(None, query, pinyin).ratio()
                score += similarity * 0.3

        return min(1.0, score)

    def _calculate_basic_match_score(self, region: Dict, query: str) -> float:
        score = 0.0
        name = region["name"].lower()

        # Strip common suffixes for more flexible matching
        short_name = name
        for s in COMMON_SUFFIXES:
            if short_name.endswith(s):
                short_name = short_name[:-len(s)]
                break

        if query == name or query == short_name:
            score += self.config["boost_exact_match"]
        elif name.startswith(query) or short_name.startswith(query):
            score += self.config["boost_prefix_match"]
        elif query in name or query in short_name:
            score += 0.5
        elif name in query or short_name in query:
            score += 0.4

        if region.get("pinyin"):
            pinyin = region["pinyin"].lower().replace(" ", "")
            pinyin_short_ver = pinyin
            if pinyin.endswith("sheng"):
                pinyin_short_ver = pinyin[:-5]
            elif pinyin.endswith("shi"):
                pinyin_short_ver = pinyin[:-3]

            if query == pinyin or query == pinyin_short_ver:
                score += self.config["boost_exact_match"] * 0.8
            elif pinyin.startswith(query) or pinyin_short_ver.startswith(query):
                score += self.config["boost_prefix_match"] * 0.6
            elif query in pinyin or query in pinyin_short_ver:
                score += 0.4
            elif pinyin in query or pinyin_short_ver in query:
                score += 0.3

        if region.get("pinyin_short"):
            short = region["pinyin_short"].lower()
            if query == short:
                score += 1.0
            elif short.startswith(query):
                score += 0.8
        return score

    def _calculate_position_score(self, region: Dict, query: str) -> float:
        name = region["name"].lower()
        # Find match for any part of name in query or vice versa
        pos = name.find(query)
        if pos == -1:
            # Check if name is in query
            pos = query.find(name)
            if pos == -1: return 0.0
            return max(0.0, 1.0 - pos / len(query))

        return max(0.0, 1.0 - pos / len(name))

    def _get_match_type(self, code: str, query: str) -> str:
        region = self.index["code_to_region"][code]
        name = region["name"].lower()

        short_name = name
        for s in COMMON_SUFFIXES:
            if short_name.endswith(s):
                short_name = short_name[:-len(s)]
                break

        if query == name or query == short_name: return "exact_name"
        if name.startswith(query) or short_name.startswith(query): return "prefix_name"
        if name in query or short_name in query: return "part_name"

        if region.get("pinyin"):
            pinyin = region["pinyin"].lower().replace(" ", "")
            pinyin_short_ver = pinyin
            if pinyin.endswith("sheng"):
                pinyin_short_ver = pinyin[:-5]
            elif pinyin.endswith("shi"):
                pinyin_short_ver = pinyin[:-3]

            if query == pinyin or query == pinyin_short_ver: return "exact_pinyin"
            if pinyin.startswith(query) or pinyin_short_ver.startswith(query): return "prefix_pinyin"
            if pinyin in query or pinyin_short_ver in query: return "part_pinyin"

        if region.get("pinyin_short"):
            short = region["pinyin_short"].lower()
            if query == short: return "exact_short"
        return "fuzzy"

    def _build_full_info(self, code: str) -> Dict:
        region = self.index["code_to_region"][code]
        ancestors = self.index["ancestor_cache"].get(code, [])
        hierarchy = {}
        for anc_code in ancestors:
            anc = self.index["code_to_region"][anc_code]
            level = anc["level"]
            if "省级" in level:
                hierarchy["province"] = anc
            elif "市级" in level:
                hierarchy["city"] = anc
            elif "区县级" in level:
                hierarchy["district"] = anc

        level_rank = {"省级": 1, "市级": 2, "区县级": 3, "街道级": 4, "村级": 5}.get(region["level"], 99)
        display_path = " > ".join([self.index["code_to_region"][c]["name"] for c in ancestors])

        return {
            "current": region,
            "hierarchy": hierarchy,
            "level_rank": level_rank,
            "full_path": region.get("full_path", ""),
            "display_path": display_path
        }


class RegionSearchEngine:
    """Core search engine for administrative divisions."""

    def __init__(self, index_file: Optional[Union[str, Path]] = None):
        self.index = None
        self.search_algorithm = None
        self._init_common_patterns()

        if index_file:
            self.load_index(index_file)

    def load_index(self, filepath: Union[str, Path]):
        """Load index from binary file."""
        self.index = StorageManager.load(str(filepath))
        self.search_algorithm = FuzzySearchAlgorithm(self.index)

    def search(self, query: str, limit: int = 10, search_type: str = "auto") -> List[SearchResult]:
        if not self.index:
            raise RuntimeError("Index not loaded. Use load_index() first.")

        if search_type == "auto":
            search_type = self._detect_search_type(query)

        if search_type == "pinyin_combo":
            results = self._search_pinyin_combo(query, limit)
            if results:
                return results
            # Fallback to normal pinyin search if combo fails
            search_type = "pinyin"

        return self.search_algorithm.search(query, limit, search_type)

    def _detect_search_type(self, query: str) -> str:
        query = query.strip()
        if not query: return "name"

        q_lower = query.lower()

        # 1. Contains Chinese
        if any("\u4e00" <= c <= "\u9fff" for c in query):
            if any("a" <= c <= "z" for c in q_lower): return "mixed"
            return "name"

        # 2. Pure letters
        if q_lower.isalpha():
            if len(q_lower) <= 2: return "short"

            # Check if it could be a combo first
            if self._could_be_combo(q_lower):
                return "pinyin_combo"

            if 3 <= len(q_lower) <= 4:
                return "pinyin" if self._looks_like_pinyin(q_lower) else "short"

            return "pinyin"

        if " " in query and q_lower.replace(" ", "").isalpha(): return "pinyin"
        if any(c in q_lower for c in "-_>"): return "path"

        return "name"

    def _looks_like_pinyin(self, text: str) -> bool:
        vowels = set("aeiou")
        if not any(c in vowels for c in text): return False
        consonant_streak = 0
        for c in text:
            if c in vowels:
                consonant_streak = 0
            else:
                consonant_streak += 1
                if consonant_streak > 2: return False
        return True

    def _could_be_combo(self, text: str) -> bool:
        for p in self.common_province_pinyin:
            if text.startswith(p) or (len(p) >= 4 and text.startswith(p[:4])):
                return True
        if len(text) in [4, 5, 6]:
            for split in [2, 3]:
                if split < len(text) and text[:split] in self.common_province_shorts:
                    return True
        return False

    def _init_common_patterns(self):
        self.common_province_pinyin = {
            "beijing", "shanghai", "tianjin", "chongqing", "hebei", "shanxi", "liaoning",
            "jilin", "heilongjiang", "jiangsu", "zhejiang", "anhui", "fujian", "jiangxi",
            "shandong", "henan", "hubei", "hunan", "guangdong", "hainan", "sichuan",
            "guizhou", "yunnan", "shanxi", "gansu", "qinghai", "taiwan", "hongkong",
            "macao", "xinjiang", "ningxia", "guangxi", "neimenggu", "xizang"
        }
        self.common_province_shorts = {
            "bj", "sh", "tj", "cq", "he", "sx", "ln", "jl", "hl", "js", "zj", "ah", "fj",
            "jx", "sd", "ha", "hb", "hn", "gd", "hi", "sc", "gz", "yn", "sn", "gs", "qh",
            "nx", "xj", "tw", "hk", "mo", "gx", "nm", "xz"
        }

    def _search_pinyin_combo(self, query: str, limit: int = 10) -> List[SearchResult]:
        query = query.strip().lower()
        combos = self._parse_pinyin_combo(query)
        results = []
        for combo in combos:
            results.extend(self._execute_combo_search(combo, query))

        # Deduplicate and sort
        seen = set()
        unique = []
        for r in results:
            if r.region.code not in seen:
                seen.add(r.region.code)
                unique.append(r)

        unique.sort(key=lambda x: (x.score + (0.3 if x.match_type.endswith("_primary") else 0)), reverse=True)
        return unique[:limit]

    def _parse_pinyin_combo(self, query: str) -> List[Dict]:
        combos = []
        if 2 <= len(query) <= 6:
            if len(query) == 4:
                p_short, c_short = query[:2], query[2:]
                p_matches = self._find_by_short(p_short, "省级")
                c_matches = self._find_by_short(c_short, "市级")
                for p in p_matches:
                    for c in c_matches:
                        if c.get("parent_code") == p["code"]:
                            combos.append({"type": "short_combo", "province": p, "city": c, "score": 2.0})
        return combos

    def _find_by_short(self, short: str, level: str) -> List[Dict]:
        matches = []
        for code, reg in self.index["code_to_region"].items():
            if reg["level"] == level and reg.get("pinyin_short") == short:
                matches.append(reg)
        return matches

    def _execute_combo_search(self, combo: Dict, query: str) -> List[SearchResult]:
        results = []
        p_reg = combo["province"]
        c_reg = combo["city"]

        # City result
        full_info = self.search_algorithm._build_full_info(c_reg["code"])
        results.append(SearchResult(
            region=Region(**c_reg),
            full_info=full_info,
            score=combo["score"],
            match_type="combo_primary"
        ))

        # Districts under this city
        if c_reg["code"] in self.index["parent_inverted"]:
            for d_code in self.index["parent_inverted"][c_reg["code"]]:
                d_reg = self.index["code_to_region"][d_code]
                results.append(SearchResult(
                    region=Region(**d_reg),
                    full_info=self.search_algorithm._build_full_info(d_code),
                    score=combo["score"] * 0.7,
                    match_type="combo_district"
                ))
        return results


# Alias for backward compatibility
AddressStandardizer = RegionSearchEngine
