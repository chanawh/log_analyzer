import unittest
import pprint
from pathlib import Path
from core.log_utils import drill_down_by_program


class TestDrillDownByProgram(unittest.TestCase):
    def setUp(self):
        self.log_path = Path("test_program.log")
        self.log_path.write_text(
            "2022-01-01 12:00:00 isi_something[123]: Started process \n"
            "2022-01-01 12:01:00 celog_daemon[456]: Error occurred \n"
            "2022-01-01 12:02:00 /boot/init: Boot event\n"
            "2022-01-01 12:03:00 random_entry: Not a program\n"
        )

    def tearDown(self):
        self.log_path.unlink(missing_ok=True)

    def test_basic_grouping(self):
        grouped = drill_down_by_program(self.log_path)
        # pprint.pprint(grouped['isi_something'])  # Nicely formatted output
        self.assertIn("isi_something", grouped)
        self.assertIn("celog_daemon", grouped)
        self.assertIn("/boot/init", grouped)

        for entries in grouped.values():
            for line in entries:
                self.assertNotIn("random_entry", line)

        self.assertEqual(len(grouped["isi_something"]), 1)
        self.assertEqual(len(grouped["celog_daemon"]), 1)
        self.assertEqual(len(grouped["/boot/init"]), 1)


if __name__ == "__main__":
    unittest.main()
