# cn-address-normalizer

China address standardizer with a prebuilt index file.

## Install （use whl install first）

```bash
pip install https://github.com/harmonsir/cn-address-normalizer/releases/download/latest/cn_address_normalizer-0.0.1-py3-none-any.whl
```

## Usage

```python
from address_standardizer import AddressNormalizer

normalizer = AddressNormalizer()
normalizer.load("address_standardizer.bin")
print(normalizer.normalize("china"))
```

More examples:

```python
from address_standardizer import AddressNormalizer

normalizer = AddressNormalizer()
normalizer.load("address_standardizer.bin")

queries = [
    "GD",
    "guangdong",
    "广东",
    "深圳",
    "SZ",
    "china",
    "YUG",
]

for q in queries:
    print(q, "=>", normalizer.normalize(q))
```

```python
from address_standardizer import AddressNormalizer

normalizer = AddressNormalizer()
normalizer.load("address_standardizer.bin")

print(normalizer.normalize("广东 深圳"))
print(normalizer.normalize("北京"))
```

## Build Dataset

`build_dataset.py` is the training/build script for `address_standardizer.bin`. It reads:

- `administrative_divisions_v2.json`
- `iso3166-1.json`
- `iso3166-3.json`
- [`worldcities.csv`](https://simplemaps.com/data/world-cities)

The script uses `pypinyin` to generate pinyin variants and then saves the index file. Adjust the paths as needed.

```bash
pip install pypinyin
python build_dataset.py
```

## Files

- `address_standardizer.py`
- `address_standardizer.bin`

---

# cn-address-normalizer

基于预构建索引的中国地址标准化工具。

## 安装（先使用whl安装）

```bash
pip install https://github.com/harmonsir/cn-address-normalizer/releases/download/latest/cn_address_normalizer-0.0.1-py3-none-any.whl
```

## 用法

```python
from address_standardizer import AddressNormalizer

normalizer = AddressNormalizer()
normalizer.load("address_standardizer.bin")
print(normalizer.normalize("china"))
```

更多示例：

```python
from address_standardizer import AddressNormalizer

normalizer = AddressNormalizer()
normalizer.load("address_standardizer.bin")

queries = [
    "GD",
    "guangdong",
    "广东",
    "深圳",
    "SZ",
    "china",
    "YUG",
]

for q in queries:
    print(q, "=>", normalizer.normalize(q))
```

```python
from address_standardizer import AddressNormalizer

normalizer = AddressNormalizer()
normalizer.load("address_standardizer.bin")

print(normalizer.normalize("广东 深圳"))
print(normalizer.normalize("北京"))
```

## 训练集构建

`build_dataset.py` 是 `address_standardizer.bin` 的训练/构建脚本，会读取：

- `administrative_divisions_v2.json`
- `iso3166-1.json`
- `iso3166-3.json`
- `worldcities.csv`

脚本使用 `pypinyin` 生成拼音变体并保存索引文件，需要按实际路径调整。

```bash
pip install pypinyin
python build_dataset.py
```

## 文件

- `address_standardizer.py`
- `address_standardizer.bin`
