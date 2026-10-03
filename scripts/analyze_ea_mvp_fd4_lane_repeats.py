"""Descriptive tap-repeat tally from the frozen FD-4 song receipt.

This is an observational comparison, not a matched experiment or a new run.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "work/ea_mvp_fd5_lazer_chart_input_v4.json"
TRACE = ROOT / "runs/ea_mvp/fd4_chart_playback_v4.json"


def main() -> None:
    chart = json.loads(CHART.read_text(encoding="utf-8"))
    receipt = json.loads(TRACE.read_text(encoding="utf-8"))
    assert chart["chart_sha256"] == receipt["chart"]["sha256"]
    assert receipt["runs"][0] == receipt["runs"][1]
    notes = chart["notes"]
    results = {
        row["note_id"]: row for row in receipt["runs"][0]["result_rows"]
        if row["component"] in ("tap", "head")
    }
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    last_in_lane: dict[int, tuple[int, dict]] = {}
    for index, note in enumerate(notes):
        previous = last_in_lane.get(note["lane"])
        if previous is not None and note["kind"] == previous[1]["kind"] == "tap":
            earlier_index, earlier = previous
            gap_us = note["start_time_us"] - earlier["start_time_us"]
            if 250_000 <= gap_us < 300_000:
                between = notes[earlier_index + 1:index]
                other_lane_between = any(
                    earlier["start_time_us"] < item["start_time_us"] < note["start_time_us"]
                    and item["lane"] != note["lane"] for item in between
                )
                group = "return_after_other_lane" if other_lane_between else "direct_repeat"
                counts[group][results[note["id"]]["result"]] += 1
        last_in_lane[note["lane"]] = index, note
    print("250-300 ms gap between consecutive taps in the same lane")
    for group in ("direct_repeat", "return_after_other_lane"):
        tally = counts[group]
        print(f"{group}: {sum(tally.values())} notes, {tally['MISS']} MISS, {dict(tally)}")
    assert sum(counts["direct_repeat"].values()) == 158
    assert counts["direct_repeat"]["MISS"] == 53
    assert sum(counts["return_after_other_lane"].values()) == 27
    assert counts["return_after_other_lane"]["MISS"] == 0


if __name__ == "__main__":
    main()
