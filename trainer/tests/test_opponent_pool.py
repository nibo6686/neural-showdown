import random
import unittest

from neural.opponent_pool import OpponentPool, OpponentSpec


class OpponentPoolTest(unittest.TestCase):
    def test_sampling_uses_positive_weight_entries(self):
        pool = OpponentPool(
            [
                OpponentSpec(name="never", type="random", weight=0.0),
                OpponentSpec(name="always", type="heuristic", weight=1.0),
            ],
            rng=random.Random(123),
        )
        for _ in range(10):
            self.assertEqual(pool.sample().name, "always")

    def test_from_config(self):
        pool = OpponentPool.from_config(
            {
                "opponents": {
                    "pool": [
                        {"name": "random", "type": "random", "weight": 0.2},
                        {"name": "heuristic", "type": "heuristic", "weight": 0.8},
                    ]
                }
            },
            rng=random.Random(1),
        )
        self.assertEqual(len(pool.opponents), 2)


if __name__ == "__main__":
    unittest.main()
