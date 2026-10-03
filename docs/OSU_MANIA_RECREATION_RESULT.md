# Playable 4K osu!mania recreation: build and comparison

**Build state (2026-10-03):** A native Python/Pygame 4K client is playable from
map selection through results. The user has deferred choosing real maps, so
map-level parity and a live comparison with an installed osu! client remain
unverified. The pinned osu!lazer source and its executable test host provide
the comparison below. This report closes the generic recreation build; it does
not claim every `.osu` map is compatible.

**Later map check:** The user selected Freedom Dive 4K Normal. Its complete
map object comparison and ideal replay passed; see the
[map-specific result](OSU_MANIA_FREEDOM_DIVE_NORMAL_RESULT.md). The paragraph
above preserves the state at the initial generic-build checkpoint.

## Run it

Install Python 3.11+ and `python -m pip install -e ".[mania]"` from the repo
root. Run `spacefly-mania` or `python -m project_b.osu.playable` and press **O**
to choose a `.osu` or `.osz` file. A map, package, or directory may also be
passed on the command line. On Windows, the supplied launcher in the task's
outputs folder opens the map chooser; a `.osu` or `.osz` file can be dragged
onto it. Maps need their audio and must be native Mode 3, 4 key maps.

Controls: **D F J K** play the four lanes, **P** pauses or resumes, **R**
restarts, **Esc** returns to map selection, and **↑/↓** select a map. Holds
require keeping the key down and releasing near their tail. The game shows
score, accuracy, combo, judgement feedback, and final results. It retains all
parsed tap and hold objects, including chords, instead of substituting taps
for holds.

## Compared with pinned osu!lazer

Reference: osu!lazer `2026.1001.0-tachyon`, Git commit
`da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9` in
`work/osu_lazer_reference`.

| Area | Recreation | Comparison evidence |
| --- | --- | --- |
| 4K tap judgement, combo and Score V2 | Implemented | Frozen four-lane tap replay corpus matches the pinned `ReplayPlayer` results and scores. |
| Hold heads, body breaks, tail releases, combo, accuracy and score | Implemented | Six hold traces run through the pinned `ReplayPlayer`; all event sequences and per-event score snapshots match. |
| Tempo and inherited scroll changes | Implemented | Uses the pinned source's duration-weighted common beat length, timing/scroll multipliers and default scroll time. Tested on a tempo case where counting timing points would be wrong. |
| `.osu`/`.osz` intake | Implemented for native 4K tap/hold maps | Parser and safe package extraction tests cover retained objects, audio lookup, negative timing offsets and unsupported-object rejection. No user-selected map corpus was available. |
| Audio and play session | Implemented with Pygame music and one wall clock for rendering and input | Synthetic WAV map completes from selection to results in a dummy audio/video smoke test. Live audio latency and actual-device sync remain unmeasured. |
| Client UI and sound | Functional, simple four-lane playfield with click feedback and explicit custom hit samples | This is not a visual or full sound-system reproduction of osu!lazer. Default/sample-bank hitsounds use a synthesized click; skins, menus, replay export, mods, and rate changes are absent. |

The reference's long-note comparison is executable with
`python scripts/run_lazer_hold_probe.py`. The Python regression is
`python -m unittest tests.test_mania_playable`. The Pygame dummy-device
end-to-end smoke is `python work/playable_smoke.py` with
`SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`.

## Limits and remaining comparison

The first real user map and assets have not been supplied. The remaining
map-level check is to load each chosen `.osu`/`.osz`, verify every parsed tap
and hold against its source row, play it on a real device, and replay matched
input through this client and pinned osu!lazer from start to results. The
present six hold cases and small tap corpus do not prove parity for arbitrary
overlapping notes, unusual maps, or full songs. The app does not support other
key counts, converted modes, mods, or playback rates. It reports unsupported
objects rather than silently dropping them. `work` and downloaded reference
source are local verification assets, not redistributable game assets.
