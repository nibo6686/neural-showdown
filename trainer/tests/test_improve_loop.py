import tempfile
import time
import unittest
from pathlib import Path

from neural.improve_loop import load_state, rotate_checkpoints, save_state


class ImproveLoopStateTest(unittest.TestCase):
    def test_state_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            self.assertEqual(load_state(path)["current_cycle"], 0)
            save_state(path, {"current_cycle": 3, "history": [{"score": 0.75}]})
            self.assertEqual(load_state(path)["current_cycle"], 3)
            self.assertEqual(load_state(path)["history"][0]["score"], 0.75)

    def test_rotate_checkpoints_keeps_newest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            paths = []
            for index in range(4):
                path = directory / f"cycle_{index:04d}.pt"
                path.write_text(str(index), encoding="utf-8")
                paths.append(path)
                time.sleep(0.01)
            rotate_checkpoints(directory, keep=2)
            remaining = sorted(path.name for path in directory.glob("cycle_*.pt"))
            self.assertEqual(remaining, [paths[2].name, paths[3].name])


if __name__ == "__main__":
    unittest.main()
