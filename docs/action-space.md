# Action Space

The model head has fixed size `13`.

Indices:

- `0-3`: `move 1` to `move 4`
- `4-7`: `move 1 terastallize` to `move 4 terastallize`
- `8-12`: up to five bench switches in bench-order

The concrete Showdown command for an index depends on the current request. `legal_actions.actions[index]` stores the concrete choice string, while `legal_actions.mask[index]` states whether that index is currently legal.

Illegal indices must be masked before sampling or argmax.
