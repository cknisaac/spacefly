# EA-MVP FD-6 — saved-trace replay companion

**Status: PASS for deterministic replay and renderer integration.**

Added `src/project_b/ea_mvp/replay_companion.py` as a separate viewer. It reuses the existing map loader, audio asset in the imported `.osz`, `ScrollMap`, Pygame note renderer, and `ManiaGame`; the existing playable app source was not changed. It reads the passing FD-4 action receipt, verifies the exact chart hash and frozen-weight/no-feedback flags, and displays the run as a **saved fly replay**, not live neural activity.

The viewer replays D/F/J/K transitions, taps, holds, judgements, score, and combo. Left/right seek by five seconds, P pauses/resumes, R restarts, and Esc closes. Seeking rebuilds the game state by replaying saved transitions up to the selected time. Manual D/F/J/K input is ignored. Scroll speed comes from the pinned chart's timing and scroll points; the viewer does not change the map or add an in-map speed adjustment.

Validation replayed all 2,618 saved transitions and reproduced the exact ordered 1,580 game event rows and FD-4 final result: score 603,684, accuracy 88.872365%, max combo 94, with no stuck keys. A Pygame dummy-display/audio smoke run rendered the results screen at 1050×760. This validates the rendering path; it is not a manual review on the user's physical display/audio device.

Run from the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m project_b.ea_mvp.replay_companion
```

Use `--map` and `--trace` to select other paths. The companion accepts only the exact frozen Freedom Dive chart and its passing FD-4 receipt. Validation script: `scripts/validate_ea_mvp_fd6_replay_companion.py`.
