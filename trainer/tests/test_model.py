import unittest

import torch

from neural.featurize import GLOBAL_DIM, POKEMON_DIM, REQUEST_DIM
from neural.models import PolicyValueMLP


class PolicyValueModelTest(unittest.TestCase):
    def test_forward_shapes(self):
        input_size = GLOBAL_DIM + 6 * POKEMON_DIM + 6 * POKEMON_DIM + REQUEST_DIM
        model = PolicyValueMLP(input_size=input_size, hidden_sizes=[64, 64])
        logits, values = model(torch.randn(5, input_size))
        self.assertEqual(tuple(logits.shape), (5, 13))
        self.assertEqual(tuple(values.shape), (5,))


if __name__ == "__main__":
    unittest.main()
