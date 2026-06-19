# Slice 2 Item/Ability Counterfactual Report

**Version:** `live-private-belief-v4`  
**Dimension:** 765  
**Method:** synthetic, protocol-faithful isolated mutations

## Item results

| Comparison | Distinguishing v4 fields |
| --- | --- |
| unknown vs confirmed no item | `item_state_unknown` vs `item_state_none`; source unknown vs request |
| unknown vs Heavy-Duty Boots | two stable current-item hash buckets; state held; source protocol |
| Boots held vs Knocked Off | current item buckets clear; same Boots buckets move to last-item; state removed |
| Boots held vs consumed item | current item clears; consumed item's last-item buckets set; state consumed |
| Boots active vs Magic Room | `item_suppressed` changes from 0 to 1 |

The tested Heavy-Duty Boots identity activates:

- current item hash family A bucket 18;
- current item hash family B bucket 24.

After Knock Off, those same two identity positions are active under
`last_item`, while current item is empty and state is `removed`.

## Ability results

| Comparison | Distinguishing v4 fields |
| --- | --- |
| unknown vs Static known | base/current Static hash buckets; state known; source protocol |
| base Static vs current Insomnia | base hashes stay Static; current hashes change; state changed |
| Static active vs suppressed | state known → suppressed; `ability_suppressed` 0 → 1 |
| confirmed no ability vs unknown | state none vs unknown; source request vs unknown |

The changed-ability fixture uses public protocol equivalent to Worry Seed:

```text
|-ability|p1a: Pikachu|Static
|-ability|p1a: Pikachu|Insomnia|[from] move: Worry Seed
```

The suppressed fixture uses public `|-endability|`, corresponding to direct
suppression such as Gastro Acid.

## Perspective sanity

The same physical p1 Boots/Static state maps as follows:

| Perspective | Item slot | Ability slot |
| --- | --- | --- |
| p1 | own held/current item | own known/current ability |
| p2 | opponent held/current item | opponent known/current ability |

Identity bucket vectors are identical across the flip; only relative side
placement changes.

## Limitations

- Fixtures are synthetic protocol transitions, not seeded random-battle move
  searches. They isolate representation and follow Showdown's public protocol.
- Dual hash buckets can theoretically collide.
- Neutralizing Gas is represented through ability identity, while direct
  per-Pokémon suppression is currently asserted only for explicit
  `-endability`.
- This slice does not train or evaluate a v4 model.
