import unittest

from address_standardizer import load_standardizer


class TestAddressStandardizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standardizer = load_standardizer("cn")

    def test_exact_match(self):
        results = self.standardizer.standardize("广东")
        self.assertTrue(any(r[0] == "Guangdong" or "广东" in str(r) for r in results))

    def test_fuzzy_match(self):
        # Test with a slight typo or lowercase
        results = self.standardizer.standardize("guangdon")
        self.assertGreater(len(results), 0)

    def test_substring_match(self):
        results = self.standardizer.standardize("中国广东深圳")
        # Should match multiple levels
        self.assertGreater(len(results), 1)


if __name__ == "__main__":
    unittest.main()
