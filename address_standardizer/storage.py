import hashlib
import logging
import pickle
import struct
import zlib
from typing import Any


logger = logging.getLogger(__name__)


class StorageManager:
    """Handles saving and loading of the index with checksum and compression."""
    MAGIC = b"RIDX"
    VERSION = 1

    @classmethod
    def save(cls, filepath: str, data: Any, compress: bool = True):
        """Save data to a binary file with optional compression."""
        try:
            serialized_data = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

            flags = 0
            if compress:
                serialized_data = zlib.compress(serialized_data)
                flags |= 1  # bit 0: compression enabled

            checksum = hashlib.sha256(serialized_data).digest()

            with open(filepath, "wb") as f:
                f.write(cls.MAGIC)
                f.write(struct.pack("B", cls.VERSION))
                f.write(struct.pack("B", flags))
                f.write(struct.pack("Q", len(serialized_data)))
                f.write(serialized_data)
                f.write(checksum)
            logger.debug(f"Successfully saved index to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save index to {filepath}: {e}")
            raise

    @classmethod
    def load(cls, filepath: str) -> Any:
        """Load data from a binary file with checksum verification."""
        try:
            with open(filepath, "rb") as f:
                if f.read(4) != cls.MAGIC:
                    raise ValueError(f"Invalid file format in {filepath}")

                version = struct.unpack("B", f.read(1))[0]
                flags = struct.unpack("B", f.read(1))[0]
                data_len = struct.unpack("Q", f.read(8))[0]
                data = f.read(data_len)
                checksum = f.read(32)

                if hashlib.sha256(data).digest() != checksum:
                    raise ValueError(f"Checksum mismatch for {filepath}")

                is_compressed = bool(flags & 1)
                if is_compressed:
                    data = zlib.decompress(data)

                return pickle.loads(data)
        except FileNotFoundError:
            logger.error(f"Index file not found: {filepath}")
            raise
        except Exception as e:
            logger.error(f"Failed to load index from {filepath}: {e}")
            raise
