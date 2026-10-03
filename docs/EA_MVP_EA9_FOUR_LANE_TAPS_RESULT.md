# EA-MVP EA-9: sequential four-lane taps

**2026-10-03 — v1 FAIL on a bookkeeping gate; v2 PASS.** Both runs are retained. The failed v1 receipt was not overwritten. Strict biology results and the saved osu! recreation were not changed.

## Frozen scope

One headless OD8 map contained four nonoverlapping taps, one per lane, each shown 500 ms before its target. The retained KC→MBON05 weights came from the first predeclared fixed-speed seed (907), whose training used lane-0 isolated notes only. No extra training occurred on this map. The map used one continuous neural simulation, persistent weights and the EA-8 fixed identity lane selector.

**ENGINEERING ASSUMPTION:** current visible lane identity is forwarded to the fixed key readout; MBON05 controls press timing only. This result tests shared timing-weight transfer to four lane outputs, not learned lane identity.

## Result

The trained arm emitted exactly four DOWN/UP pairs on lanes 0, 1, 2 and 3. DOWNs occurred at 501,000, 1,251,000, 2,001,000 and 2,751,000 µs, each 1 ms after the corresponding visible approach began and within the frozen Good window. All four judgements were PERFECT. One neural simulator served the map; the readout rearmed four times; weights remained unchanged; two replays were identical. The matched initial-weight arm emitted no DOWN and received four MISSes.

| Gate | Result |
|---|---|
| Correct lane and first DOWN for all four taps | PASS |
| Four PERFECT judgements | PASS |
| One neural initialization, four readouts, no extra actions | PASS in v2 |
| Initial-weight control silent, four MISSes | PASS |
| Weights fixed and exact replay | PASS |

## Preserved v1 audit failure

EA-9 v1 produced the correct actions and judgements but failed because `readout_rearm_count` remained 1. The lane-specific readout override created later readouts without incrementing that diagnostic counter. The issue did not affect neural state, action timing, game input or weights. The v2 code adds the missing counter increment; no model parameter or behavior rule changed. The v1 result remains at `runs/ea_mvp/four_lane_taps_v1.json`; v2 is at `runs/ea_mvp/four_lane_taps_v2.json`.

Frozen protocols: `configs/ea_mvp_four_lane_taps_v1.json` and `configs/ea_mvp_four_lane_taps_v2.json`.

## Claim boundary and next step

The narrow pass is sequential four-lane tap playback in the headless game using lane-0-trained timing weights plus the explicitly fixed lane selector. It does not show simultaneous notes/chords, dense patterns, four-lane weight learning, holds, actual client input, or biological lane encoding. The next roadmap gate is simultaneous multi-lane/chord admission, with no overlapping-note support assumed until explicitly tested.
