# Address Standardizer (v1.0.0)

Professional, high-performance address search and standardization library for Chinese administrative divisions.

## New in v1.0.0

- **Advanced Search Logic**: Support for Pinyin Combo (e.g., `gdfs` -> Guangdong Foshan), multi-strategy parallel
  searching (Exact -> Trie -> N-gram -> Fuzzy).
- **Industrial Storage**: Unified binary format (`RIDX`) with SHA256 checksums and zlib compression.
- **Modern Architecture**: Refactored into specialized modules (`base`, `builder`, `engine`, `storage`, `utils`).

## Features

- **Blazing Fast**: Uses Bitmap indices and Trie structures for O(m) prefix matching.
- **Smart Detection**: Automatically detects search types (Name, Pinyin, Short Pinyin, Combo Pinyin, Path).
- **Scoring System**: Sophisticated scoring based on match position, level rank, and path context.
- **Fuzzy Fallback**: Integrated Levenshtein-based matching for handling typos.

## Installation

```bash
pip install .
```

## Quick Start

```python
from address_standardizer import load_standardizer


# Automatically discovers built-in indices
standardizer = load_standardizer("cn")

# Complex pinyin combo search
results = standardizer.search("gdfs", limit=3)
for res in results:
    print(f"{res.region.name} - Score: {res.score:.2f} - Path: {res.full_info['display_path']}")
```

## Usage

### Auto-detection Search
```python
# Search by Chinese Name
standardizer.search("广东佛山")

# Search by Pinyin
standardizer.search("guangdong")

# Search by Short Pinyin
standardizer.search("gd")

# Search by Hierarchy Path
standardizer.search("广东省>佛山市")
```

### Building Your Own Index
```python
import json
from address_standardizer import RegionIndexBuilder


# Load your custom JSON data
with open("data.json", "r", encoding="utf-8") as f:
    regions = json.load(f)

# Build and save
builder = RegionIndexBuilder(regions)
builder.build_all_indices()
builder.save_to_file("custom_index.bin")
```

## Technical Architecture

- **`builder.py`**: Pipeline for constructing multi-level indices (Inverted, Trie, N-gram, Bitmap).
- **`engine.py`**: Core `RegionSearchEngine` implementing the search type detection flowchart and scoring.
- **`storage.py`**: Secure binary I/O with checksum verification and compression.
- **`utils.py`**: Optimized data structures like `BitmapIndex` for high-concurrency set operations.

## Roadmap

- [x] Pinyin Combo support
- [x] Administrative Division v2 support (CN)
- [ ] Global multi-region support
- [ ] GPS/Coordinate integration
- [ ] High-concurrency C++ extension for core matching

---

# 地址标准化工具 (v1.0.0)

高性能、工业级的中国行政区划搜索与标准化库。

## 特性

- **智能识别**: 自动检测输入类型（中文、全拼、首字母、组合拼音、路径）。
- **极速检索**: 基于位图索引 (Bitmap) 和前缀树 (Trie) 实现微秒级响应。
- **组合拼音**: 支持 `gdfs` (广东佛山) 等极其简便的拼音组合搜索。
- **多维度评分**: 结合匹配位置、行政层级权重和路径完整度进行综合排序。
