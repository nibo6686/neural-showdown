import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from neural.config import resolve_process_spec


class ProcessSpecTest(unittest.TestCase):
    def test_resolve_process_spec_uses_env_override(self):
        config = {"_config_path": str(Path(__file__).resolve())}
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "NEURAL_SIM_CORE_COMMAND_JSON": '["node","dist/src/server.js"]',
                    "NEURAL_SIM_CORE_CWD": temp_dir,
                },
                clear=False,
            ):
                command, cwd = resolve_process_spec(config)

        self.assertEqual(command, ["node", "dist/src/server.js"])
        self.assertEqual(cwd, str(Path(temp_dir).resolve()))

    def test_resolve_process_spec_uses_config_when_no_env_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_root = Path(temp_dir)
            config_path = config_root / "configs" / "test.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("{}", encoding="utf-8")

            config = {
                "_config_path": str(config_path),
                "sim_core": {"command": ["node", "dist/src/server.js"], "cwd": "../sim-core"},
            }
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("NEURAL_SIM_CORE_COMMAND_JSON", None)
                os.environ.pop("NEURAL_SIM_CORE_CWD", None)
                command, cwd = resolve_process_spec(config)

        self.assertEqual(command, ["node", "dist/src/server.js"])
        self.assertEqual(cwd, str((config_root / "sim-core").resolve()))


if __name__ == "__main__":
    unittest.main()
