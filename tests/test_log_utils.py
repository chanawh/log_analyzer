import unittest
from pathlib import Path
from core.log_utils import filter_log_lines

class TestFilterLogLines(unittest.TestCase):
    def setUp(self):
        # Create a temporary log file with different lines for testing
        self.test_log = Path("test_filter.log")
        self.test_log.write_text(
            "2022-01-01 info: Started\n"
            "2022-01-02 error: Failed\n"
            "2022-01-03 info: Completed\n"
            "2022-01-04 info: Another event\n"
        )

    def tearDown(self):
        # Remove the file after each test
        self.test_log.unlink(missing_ok=True)

    def test_no_filters_returns_all(self):
        lines = filter_log_lines(self.test_log)
        self.assertEqual(len(lines), 4)

    def test_keyword_filter(self):
        # Lines containing 'error'
        lines = filter_log_lines(self.test_log, keyword="error")
        self.assertEqual(lines, ["2022-01-02 error: Failed"])

    def test_start_date_filter(self):
        # Only lines from 2022-01-02 onwards
        lines = filter_log_lines(self.test_log, start_date="2022-01-02")
        self.assertEqual(
            lines,
            [
                "2022-01-02 error: Failed",
                "2022-01-03 info: Completed",
                "2022-01-04 info: Another event"
            ]
        )

    def test_end_date_filter(self):
        # Only lines up to 2022-01-03
        lines = filter_log_lines(self.test_log, end_date="2022-01-03")
        self.assertEqual(
            lines,
            [
                "2022-01-01 info: Started",
                "2022-01-02 error: Failed",
                "2022-01-03 info: Completed"
            ]
        )

    def test_date_range_filter(self):
        # Only lines between 2022-01-02 and 2022-01-03
        lines = filter_log_lines(self.test_log, start_date="2022-01-02", end_date="2022-01-03")
        self.assertEqual(
            lines,
            [
                "2022-01-02 error: Failed",
                "2022-01-03 info: Completed"
            ]
        )

if __name__ == '__main__':
    unittest.main()