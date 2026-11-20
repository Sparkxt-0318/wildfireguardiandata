# Score card: wx+prox

contract `7cb5b4bda119` · split `d94a223cf441` (space, fold test, 35 fires; threshold from 18 validation fires) · predictions `efefd741f783`

## Precision / recall / F1 at the validation threshold

| tolerance | reading | wx+prox P / R / F1 | persistence P / R / F1 | climatology P / R / F1 |
|---|---|---|---|---|
| loose | interval | 1.000 / 0.989 / 0.995 | 1.000 / 0.999 / 1.000 | 0.067 / 0.631 / 0.121 |
| loose | strict | 1.000 / 0.988 / 0.994 | 1.000 / 0.999 / 0.999 | 0.059 / 0.620 / 0.109 |
| mid | interval | 0.996 / 0.980 / 0.988 | 1.000 / 0.995 / 0.997 | 0.031 / 0.457 / 0.058 |
| mid | strict | 0.994 / 0.971 / 0.982 | 1.000 / 0.995 / 0.997 | 0.025 / 0.442 / 0.047 |
| strict | interval | 0.783 / 0.947 / 0.857 | 1.000 / 0.984 / 0.992 | 0.015 / 0.267 / 0.028 |
| strict | strict | 0.468 / 0.616 / 0.531 | 0.556 / 0.537 / 0.546 | 0.009 / 0.258 / 0.017 |

## Predicted area over true area; hard negatives; events

| | wx+prox | persistence | climatology |
|---|---|---|---|
| threshold | 0.98340696 | 1.0 | 0.00727004 |
| predicted / true area | 1.32 | 0.96 | 29.23 |
| false-alarm rate on hard negatives | 0.0016 | 0.0011 | 0.0832 |
| events detected / events | 181 / 195 | 191 / 195 | 92 / 195 |
| lead days q25 / median / q75 | 0 / 1 / 2 | 0 / 0 / 2 | 2 / 2 / 2 |

Cells excluded as unknown: 749953 of 13849060 scored cell-days (0.054152). Rule: fire=active>0; no_fire=no detection & M11,I2,I1>0 for all sub-cells; else unknown

## Lift (F1 difference, 95% cluster bootstrap over fires)

- wx+prox_minus_climatology [loose/interval]: +0.8740 (+0.8183, +0.9416)  *
- wx+prox_minus_climatology [loose/strict]: +0.8855 (+0.8367, +0.9455)  *
- wx+prox_minus_climatology [mid/interval]: +0.9298 (+0.9008, +0.9627)  *
- wx+prox_minus_climatology [mid/strict]: +0.9356 (+0.9145, +0.9605)  *
- wx+prox_minus_climatology [strict/interval]: +0.8297 (+0.7983, +0.8492)  *
- wx+prox_minus_climatology [strict/strict]: +0.5144 (+0.4062, +0.5854)  *
- wx+prox_minus_persistence [loose/interval]: -0.0049 (-0.0096, -0.0030)  *
- wx+prox_minus_persistence [loose/strict]: -0.0054 (-0.0105, -0.0033)  *
- wx+prox_minus_persistence [mid/interval]: -0.0098 (-0.0176, -0.0061)  *
- wx+prox_minus_persistence [mid/strict]: -0.0151 (-0.0255, -0.0100)  *
- wx+prox_minus_persistence [strict/interval]: -0.1350 (-0.1694, -0.1148)  *
- wx+prox_minus_persistence [strict/strict]: -0.0148 (-0.0377, +0.0045)

## Leak check

status: **pass** — declared horizon respected; AUC 0.695 on 4477 new-ignition cells (limit 0.9); front AUC 0.769 (limit 0.95). A screen, not a proof.

training provenance: not declared

card hash `398548ef096c2c1cdd915902df8e3e3dc9f9f7ca1a6ee0e4a4374d4cb39856b5`
