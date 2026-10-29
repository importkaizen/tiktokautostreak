import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tiktok_streak_keeper as tsk  # noqa: E402


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        tsk.apply_data_dir(self.data_dir)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, payload: dict) -> Path:
        path = self.data_dir / "config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_load_config_reads_targets_and_jitter(self) -> None:
        path = self._write(
            {
                "targets": ["Alice", "Bob"],
                "message": "🔥",
                "jitter_seconds": [10, 20],
                "data_dir": str(self.data_dir),
            }
        )
        cfg = tsk.load_config(path)
        self.assertEqual(cfg["targets"], ["Alice", "Bob"])
        self.assertEqual(cfg["message"], "🔥")
        self.assertEqual(cfg["jitter_seconds"], (10, 20))

    def test_rejects_placeholder_targets(self) -> None:
        path = self._write(
            {
                "targets": ["Exact display name from TikTok Messages"],
                "message": "hi",
            }
        )
        with self.assertRaises(SystemExit):
            tsk.load_config(path)

    def test_rejects_empty_message(self) -> None:
        path = self._write({"targets": ["Alice"], "message": "  "})
        with self.assertRaises(SystemExit):
            tsk.load_config(path)

    def test_init_writes_example_once(self) -> None:
        dest = self.data_dir / "config.json"
        self.assertEqual(tsk.init_config(dest), 0)
        self.assertTrue(dest.exists())
        self.assertEqual(tsk.init_config(dest), 0)


class StatusTests(unittest.TestCase):
    def test_version_constant(self) -> None:
        self.assertRegex(tsk.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
