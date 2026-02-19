import json
from pathlib import Path

from address_standardizer import load_standardizer, RegionIndexBuilder


# Configuration
SOURCE_JSON = Path(r"M:\CodeHub\pycountry-china\etl\output\administrative_divisions_v2.json")
INDEX_PATH = Path("regions_index.bin")


def verify():
    print(f"Loading source data from {SOURCE_JSON}...")
    with open(SOURCE_JSON, 'r', encoding='utf-8') as f:
        regions = json.load(f)

    print(f"Building index for {len(regions)} regions...")
    builder = RegionIndexBuilder(regions)
    builder.build_all_indices()

    print(f"Saving index to {INDEX_PATH}...")
    builder.save_to_file(str(INDEX_PATH))

    print("Loading standardizer...")
    engine = load_standardizer(index_path=INDEX_PATH)

    # Debug: check some index entries
    print("\nDebug Index Entries:")
    for code in ['440000', '440600']:
        reg = engine.index['code_to_region'].get(code)
        print(f"  Code {code}: {reg}")

    test_queries = [
        "广东佛山",  # Name
        "guangdong",  # Pinyin
        "gdfs",  # Pinyin Combo (short)
        "bj",  # Short
        "foshan",  # Pinyin
    ]

    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = engine.search(query, limit=3)
        for i, res in enumerate(results):
            print(f"  {i + 1}. {res.region.name} ({res.region.code}) - Score: {res.score:.4f}, Match: {res.match_type}")
            print(f"     Path: {res.full_info['display_path']}")


if __name__ == "__main__":
    verify()
