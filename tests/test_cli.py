import os
import subprocess
import sys
import unittest

PY = sys.executable


def run_cli(*args, env=None):
    return subprocess.run([PY, "-m", "cron_mini", *args], capture_output=True,
                          text=True, encoding="utf-8", env=env)


class TestCli(unittest.TestCase):
    def test_next_count(self):
        result = run_cli("next", "*/5 * * * *", "--now", "2026-03-04T10:07", "--count", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2026-03-04 10:10:00", result.stdout)
        self.assertIn("2026-03-04 10:15:00", result.stdout)

    def test_leap_day_start(self):
        result = run_cli("next", "* * * * *", "--now", "2024-02-29T10:00")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2024-02-29 10:01:00", result.stdout)

    def test_utf8_output_under_legacy_windows_encoding(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "cp1252"
        env.pop("PYTHONUTF8", None)
        result = subprocess.run([PY, "-m", "cron_mini", "explain", "0 9 * * 1-5"],
                                capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertIn("星期一二三四五", result.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
