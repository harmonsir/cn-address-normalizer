from __future__ import annotations

import os
from pathlib import Path

from setuptools import setup


BASE_DIR = Path(__file__).resolve().parent


def read_version() -> str:
    """读取版本号，优先使用环境变量。"""
    env_version = os.getenv("PKG_VERSION", "").strip()
    if env_version:
        return env_version.lstrip("v")
    return "0.0.1"


setup(
    name="cn-address-normalizer",
    version=read_version(),
    description="China address standardizer with prebuilt index.",
    long_description="China address standardizer with prebuilt index.",
    long_description_content_type="text/plain",
    py_modules=["address_standardizer"],
    data_files=[("", ["address_standardizer.bin"])],
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "pyahocorasick",
        "Levenshtein",
    ],
)
