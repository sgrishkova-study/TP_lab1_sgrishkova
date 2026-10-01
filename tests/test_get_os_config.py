import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class GetOsConfigTests(unittest.TestCase):
    def test_import_has_no_side_effect_file_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path.cwd()
            try:
                import os

                os.chdir(temp_dir)
                importlib.import_module("get_os_config")
                self.assertFalse(Path("ur_data.json").exists())
            finally:
                os.chdir(cwd)

    def test_read_text_missing_file_returns_none(self):
        import get_os_config

        self.assertIsNone(get_os_config.read_text("/path/that/does/not/exist"))

    def test_safe_get_user_fallback(self):
        import get_os_config

        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("getpass.getuser", side_effect=RuntimeError("x")):
                with mock.patch("os.getlogin", return_value="fallback-user"):
                    self.assertEqual(get_os_config.safe_get_user(), "fallback-user")

    def test_write_os_data_writes_json(self):
        import get_os_config

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "ur_data.json"
            with mock.patch("get_os_config.collect_os_data", return_value={"a": 1, "b": "x"}):
                get_os_config.write_os_data(path=str(output))
            self.assertTrue(output.exists())
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"a": 1, "b": "x"})


if __name__ == "__main__":
    unittest.main()
