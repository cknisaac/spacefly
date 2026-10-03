# Freedom Dive 4K Normal: recreation versus osu!lazer

**Map:** xi — FREEDOM DiVE, 4K Normal, mapped by razlteh; 2.00 stars in the
installed client's song list. The map was exported from the installed lazer
editor as `xi - FREEDOM DiVE (razlteh).osz`. The selected `.osu` SHA-256 is
`ced99e231e7eee354feef04bbcde6889178814cb688325bccdeeeacb00dcbff9`.
No original map or audio is redistributed with this report.

## Result

| Check | Outcome |
| --- | --- |
| Load the exported `.osz` and audio | Passed. The package contained nine difficulties; the recreation offered its four native 4K charts and selected 4K Normal with its MP3. |
| Parse 4K Normal against osu!lazer | Passed. All 1,310 objects have identical type, lane, start time, and end time; OD matches. There are 1,220 taps and 90 holds, and 29 timing points (28 inherited). |
| Full-chart ideal replay | Passed. Both engines returned 1,000,000 score, 100% accuracy, 1,400 maximum combo, 1,400 Perfect results, and 180 ignored hold body/parent results. The pinned lazer replay host ran its virtual track at 20× to shorten the test, without mods or changed map-time input offsets. |
| Recreation audio and UI | Passed in a dummy-device smoke test. The actual MP3 decoded, playback started, the 4K playfield rendered real notes/holds, and the result screen rendered. This does not measure physical output latency. |
| Installed lazer client | The 4K Normal chart was selected, opened in the editor, exported, and observed in its live playtest. The installed version is `2026.921.0-lazer+aaa75b7c0a9f21d558ce84cd0ffac6c739bad8e7`. Live playtest input was detected, so no further control was sent to that window. |

The executable source comparison uses pinned osu!lazer
`2026.1001.0-tachyon`, commit `da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`.
That is newer than the installed binary. The object and replay results above
are therefore exact comparisons against the pinned source test host, while
the installed client supplied the map export and live visual check.

## How to reproduce

With the same exported `.osz` still in lazer's `exports` folder, run
`python scripts/run_lazer_freedom_dive_probe.py` from the repository root.
It checks the source pin, compares all objects with the reference decoder,
and runs a full perfect `ReplayPlayer` trace. The recreation-only full-chart
audit is `PYTHONPATH=src python work/freedom_dive_audit.py`. A dummy-device
MP3/playfield/results smoke is `PYTHONPATH=src python work/freedom_dive_ui_smoke.py`
with `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`.

## Remaining differences

The recreation uses a simple playfield, synthesized default click sounds and
only explicit custom hit samples; lazer has its own skin, background, sample
banks, HUD, and menus. The actual MP3 loaded in the recreation, but no
physical audio/visual latency measurement or manual full-song play was made.
The perfect replay checks this chart's parsing and ideal input path, not every
possible early, late, missed, or broken input sequence on the full chart.
Six isolated long-note traces cover those cases in the pinned host.
