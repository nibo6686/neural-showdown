import unittest

from neural.runtime import load_runtime_options, make_battle_seed


class RuntimeOptionsTest(unittest.TestCase):
    def test_load_runtime_options_uses_defaults(self):
        runtime = load_runtime_options({"profile": "dev"}, default_num_envs=3)
        self.assertEqual(runtime.profile, "dev")
        self.assertEqual(runtime.num_envs, 3)
        self.assertEqual(runtime.retry_attempts_per_battle, 2)
        self.assertEqual(runtime.timeouts_sec["step"], 20.0)

    def test_make_battle_seed_is_deterministic(self):
        self.assertEqual(make_battle_seed(7), make_battle_seed(7))
        self.assertNotEqual(make_battle_seed(7), make_battle_seed(8))


if __name__ == "__main__":
    unittest.main()
