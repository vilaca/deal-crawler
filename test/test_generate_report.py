"""Tests for generate_report module."""

import csv
import os
import tempfile
import unittest
from pathlib import Path

from generate_report import _find_latest_csv, _read_csv, _generate_markdown, PriceRow


class TestFindLatestCsv(unittest.TestCase):
    """Test finding the latest CSV file."""

    def test_finds_latest_by_name(self):
        """Test returns the last CSV file sorted by name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["2026-04-19.csv", "2026-04-21.csv", "2026-04-20.csv"]:
                Path(tmpdir, name).touch()
            result = _find_latest_csv(Path(tmpdir))
            self.assertEqual(result.name, "2026-04-21.csv")

    def test_exits_on_empty_dir(self):
        """Test exits when no CSV files found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(SystemExit):
                _find_latest_csv(Path(tmpdir))


class TestReadCsv(unittest.TestCase):
    """Test CSV reading."""

    def test_reads_rows(self):
        """Test reads CSV into PriceRow objects."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Product", "Site", "Price", "Price per 100ml", "URL"])
            writer.writerow(["Test Product", "example.com", "10.50", "5.25", "https://example.com/p"])
            writer.writerow(["Test Product", "other.com", "12.00", "", "https://other.com/p"])
            f.flush()
            path = Path(f.name)

        try:
            rows = _read_csv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].product, "Test Product")
            self.assertEqual(rows[0].price, 10.50)
            self.assertEqual(rows[0].price_per_100ml, 5.25)
            self.assertIsNone(rows[1].price_per_100ml)
        finally:
            os.unlink(path)


class TestGenerateMarkdown(unittest.TestCase):
    """Test markdown generation."""

    def test_picks_cheapest_per_product(self):
        """Test generates markdown with cheapest price per product."""
        rows = [
            PriceRow("Product A", "expensive.com", 20.0, None, "https://expensive.com/p"),
            PriceRow("Product A", "cheap.com", 10.0, 5.0, "https://cheap.com/p"),
            PriceRow("Product B", "store.com", 15.0, None, "https://store.com/p"),
        ]
        md = _generate_markdown(rows, Path("2026-04-21.csv"))

        self.assertIn("| Product | Price | Link |", md)
        self.assertIn("10.00", md)  # Cheapest for Product A
        self.assertNotIn("20.00", md)  # Expensive one excluded
        self.assertIn("15.00", md)  # Product B
        self.assertIn("cheap.com", md)
        self.assertIn("3 prices across 2 products", md)

    def test_price_per_100ml_display(self):
        """Test price per 100ml is shown when available."""
        rows = [PriceRow("Test", "site.com", 10.0, 5.0, "https://site.com/p")]
        md = _generate_markdown(rows, Path("test.csv"))
        self.assertIn("5.00/100ml", md)

    def test_no_price_per_100ml(self):
        """Test no price per 100ml when not available."""
        rows = [PriceRow("Test", "site.com", 10.0, None, "https://site.com/p")]
        md = _generate_markdown(rows, Path("test.csv"))
        self.assertNotIn("/100ml", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
