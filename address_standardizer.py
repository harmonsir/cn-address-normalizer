import hashlib
import pickle
import struct
import zlib
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple

import ahocorasick
import Levenshtein


# --- 1. 数据模型层 ---

@dataclass(frozen=True)
class StandardEntry:
    standard_name: str
    level: str
    source_standard: str
    original_variants: tuple


@dataclass(frozen=True)
class RegionLevel:
    level: str
    priority: int


# --- 2. 持久化层 (策略模式) ---

class IndexPersistence:
    """负责索引的保存与加载，支持校验与压缩"""
    MAGIC = b"RIDX"
    VERSION = 1

    @classmethod
    def save(cls, filepath: str, data: Any):
        serialized_data = pickle.dumps(data)
        compressed_data = zlib.compress(serialized_data)
        checksum = hashlib.sha256(compressed_data).digest()

        with open(filepath, "wb") as f:
            f.write(cls.MAGIC)
            f.write(struct.pack("B", cls.VERSION))
            f.write(struct.pack("Q", len(compressed_data)))
            f.write(compressed_data)
            f.write(checksum)

    @classmethod
    def load(cls, filepath: str) -> Any:
        with open(filepath, "rb") as f:
            if f.read(4) != cls.MAGIC:
                raise ValueError("Invalid file format")

            _version = struct.unpack("B", f.read(1))[0]
            data_len = struct.unpack("Q", f.read(8))[0]
            compressed_data = f.read(data_len)
            checksum = f.read(32)

            if hashlib.sha256(compressed_data).digest() != checksum:
                raise ValueError("Checksum mismatch")

            return pickle.loads(zlib.decompress(compressed_data))


# --- 3. 核心引擎层 ---

class AddressNormalizer:
    def __init__(self):
        self.automaton = ahocorasick.Automaton()
        # entries 存储：ID -> StandardEntry 对象
        self.entries: Dict[int, StandardEntry] = {}
        self._next_id = 0

        self.level_priority = {
            "national": RegionLevel("country", 0),
            "province": RegionLevel("province", 1),
            "city": RegionLevel("city", 2),
            "county": RegionLevel("county", 3),
            "country": RegionLevel("country", 4),
        }

    def add_standard_entry(self, standard_name: str, variants: List[str], level: str, source_standard: str):
        """添加标准词条"""
        entry = StandardEntry(
            standard_name=standard_name,
            level=level,
            source_standard=source_standard,
            original_variants=tuple(variants)
        )

        entry_id = self._next_id
        self.entries[entry_id] = entry
        self._next_id += 1

        for var in variants:
            key = str(var).lower().strip()
            if key:
                # Automaton 存储 entry_id 的列表，处理多词同音/同名
                if key in self.automaton:
                    self.automaton.get(key).append(entry_id)
                else:
                    self.automaton.add_word(key, [entry_id])

    def build(self):
        """构建 Aho-Corasick 自动机"""
        self.automaton.make_automaton()

    def normalize(self, query: str, similarity_threshold: float = 0.7) -> List[Tuple]:
        """标准化入口：精确匹配优先，模糊匹配兜底"""
        query = query.lower().strip()

        # 1. 尝试全字精确匹配
        if query in self.automaton:
            ids = self.automaton.get(query)
            return self._format_results([self.entries[idx] for idx in ids])

        # 2. 尝试子串扫描匹配 (AC 自动机核心优势)
        matches = []
        for _, entry_ids in self.automaton.iter(query):
            for idx in entry_ids:
                matches.append(self.entries[idx])

        if matches:
            return self._format_results(list(set(matches)))

        # 3. 模糊搜索兜底
        return self._fuzzy_search(query, similarity_threshold)

    def _fuzzy_search(self, query: str, threshold: float) -> List[Tuple]:
        results = []
        # 注意：生产环境下如果 entries 达到万级，此处建议使用 RapidFuzz 或局部索引
        for entry in self.entries.values():
            # 比较标准名或变体
            sim = Levenshtein.ratio(query, entry.standard_name.lower())
            if sim >= threshold:
                results.append((entry.standard_name, entry.level, entry.source_standard, sim))

        return sorted(results, key=lambda x: x[3], reverse=True)

    def _format_results(self, entries: List[StandardEntry]) -> List[Tuple]:
        """排序并格式化输出"""
        sorted_entries = sorted(
            entries,
            key=lambda x: self.level_priority.get(x.level, RegionLevel("unknown", 9)).priority
        )
        return [(e.standard_name, e.level, e.source_standard, e.original_variants) for e in sorted_entries]

    # --- 持久化接口 ---

    def save(self, filepath: str):
        # 1. 对 entries 进行“脱水”：对象 -> 字典
        dehydrated_entries = {idx: asdict(e) for idx, e in self.entries.items()}

        state = {
            "entries": dehydrated_entries,  # 现在全是原生 dict
            "next_id": self._next_id,
            "automaton": self.automaton  # pyahocorasick 是 C 实现，它有自己的序列化逻辑，不依赖你的类路径
        }
        IndexPersistence.save(filepath, state)

    def load(self, filepath: str):
        state = IndexPersistence.load(filepath)

        # 2. 对 entries 进行“复写”：字典 -> 对象
        raw_entries = state["entries"]
        self.entries = {
            idx: StandardEntry(**data)  # 重新实例化
            for idx, data in raw_entries.items()
        }

        self.automaton = state["automaton"]
        self._next_id = state["next_id"]


if __name__ == '__main__':
    # --- 从文件加载 ---
    new_normalizer = AddressNormalizer()
    new_normalizer.load("address_standardizer.bin")

    # 测试加载后的结果
    print(f"加载后的输出: {new_normalizer.normalize("taiwan")}")
