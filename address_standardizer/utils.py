import array


class BitmapIndex:
    """Bitmap index for fast set operations."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.bitmap = array.array("Q")  # 64-bit integers
        self.word_count = (capacity + 63) // 64
        self.bitmap.extend([0] * self.word_count)

    def set(self, index: int):
        if 0 <= index < self.capacity:
            word_idx = index // 64
            bit_idx = index % 64
            self.bitmap[word_idx] |= (1 << bit_idx)

    def get(self, index: int) -> bool:
        if 0 <= index < self.capacity:
            word_idx = index // 64
            bit_idx = index % 64
            return bool(self.bitmap[word_idx] & (1 << bit_idx))
        return False

    def and_op(self, other: "BitmapIndex") -> "BitmapIndex":
        result = BitmapIndex(self.capacity)
        for i in range(min(self.word_count, other.word_count)):
            result.bitmap[i] = self.bitmap[i] & other.bitmap[i]
        return result

    def or_op(self, other: "BitmapIndex") -> "BitmapIndex":
        result = BitmapIndex(self.capacity)
        for i in range(min(self.word_count, other.word_count)):
            result.bitmap[i] = self.bitmap[i] | other.bitmap[i]
        return result

    def count(self) -> int:
        count = 0
        for word in self.bitmap:
            n = word
            while n:
                n &= n - 1
                count += 1
        return count


class CompressedString:
    """Lightweight string storage optimization."""

    def __init__(self, text: str):
        self.original = text
        self.compressed = self._compress(text)

    def _compress(self, text: str) -> bytes:
        if all(ord(c) < 128 for c in text):
            return text.encode("ascii")
        return text.encode("utf-8")

    @property
    def value(self) -> str:
        return self.original
