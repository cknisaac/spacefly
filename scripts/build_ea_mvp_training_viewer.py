"""Build a self-contained, read-only viewer from the saved EA-MVP receipts."""

from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "runs/ea_mvp/confirmation_fixed_v1/seed_907_learning_on.json.gz"
EVALUATION = ROOT / "runs/ea_mvp/broad_eval_v1.json"
TEMPLATE = ROOT / "visualization/ea-mvp-training-playback.template.html"
OUTPUT = ROOT / "visualization/ea-mvp-training-playback.html"
PATTERNS = (
    ("dense_lane_switch_taps", "Lane switches"),
    ("new_chord_lane_sets", "Chords"),
    ("new_sequential_hold_lengths", "Hold notes"),
)


def ms(value: int | None) -> float | None:
    return None if value is None else round(value / 1000, 3)


def action_rows(rows: list[dict]) -> list[list]:
    return [[ms(row["time_us"]), row["lane"], row["kind"] == "down"]
            for row in rows]


def result_rows(rows: list[dict]) -> list[list]:
    # The saved game's callback order is not always chronological for hold
    # misses. Sort only for presentation, retaining order at tied times.
    return [[ms(row["time_us"]), row["lane"], row["result"], row["note_id"],
             row["component"]] for row in sorted(rows, key=lambda item: item["time_us"])]


def test_notes(results: list[dict]) -> list[list]:
    by_id: dict[str, dict] = {}
    for row in results:
        if row["component"] in ("tap", "head"):
            by_id[row["note_id"]] = {
                "lane": row["lane"], "head": row["note_time_us"],
                "tail": row["note_time_us"],
            }
        elif row["component"] == "tail":
            by_id[row["note_id"]]["tail"] = row["note_time_us"]
    return [[ms(value["head"]), ms(value["tail"]), value["lane"], note_id]
            for note_id, value in sorted(by_id.items(), key=lambda pair: (
                pair[1]["head"], pair[1]["lane"]))]


def build() -> None:
    with gzip.open(TRAINING, "rt", encoding="utf-8") as stream:
        source = json.load(stream)
    broad = json.loads(EVALUATION.read_text(encoding="utf-8"))
    assert source["seed"] == 907 and source["arm"] == "learning_on"
    episodes = source["training_episodes"]
    assert len(episodes) == 500
    first_press = next(row["episode"] for row in episodes if row["first_down_us"] is not None)
    assert first_press == 359
    assert Counter(row["game_results"][0]["result"] for row in episodes) == {
        "MISS": 358, "PERFECT": 142,
    }
    changed = source["changed_slots"]
    assert changed == list(range(7))
    kc_ids = [row["result"]["changes"][index]["kc_source_id"]
              for row in episodes[0]["local_teaching"] for index in range(7)]
    trials = []
    for row in episodes:
        teaching = row["local_teaching"][0]
        pulse = teaching["pulse"]
        result = teaching["result"]
        trials.append({
            "n": row["episode"],
            "actions": action_rows(row["actions"]),
            "judgement": row["game_results"][0]["result"],
            "judgementMs": ms(row["game_results"][0]["time_us"]),
            "feedbackMs": ms(row["feedback"][0]["delivered_at_us"]),
            "pulseMs": None if pulse is None else ms(pulse["onset_us"]),
            "danSpikeMs": None if not result["dan_spikes"] else ms(result["dan_spikes"][0][1][0]),
            "creditedKCs": len(result["credited_kc_spikes"]),
            "changed": len(result["changes"]),
            "before": [round(row["weights_before"][index], 9) for index in changed],
            "after": [round(row["weights_after"][index], 9) for index in changed],
        })
    assert trials[0]["pulseMs"] == 628 and trials[0]["danSpikeMs"] == 642
    assert all(row["pulseMs"] is None for row in trials[first_press - 1:])
    assert all(row["changed"] == 0 for row in trials[first_press - 1:])

    tests: dict[str, dict] = {}
    for key, title in PATTERNS:
        cases = broad["seeds"]["907"][key]
        reference = cases["learning_on"]["record"]
        notes = test_notes(reference["results"])
        arms = {}
        for arm in ("learning_on", "shuffled_teaching", "untrained"):
            record = cases[arm]["record"]
            arms[arm] = {
                "actions": action_rows(record["actions"]),
                "results": result_rows(record["results"]),
                "score": record["score"],
            }
        duration = max([row[1] for row in notes] + [0]) + 500
        tests[key] = {"title": title, "notes": notes, "durationMs": duration, "arms": arms}

    payload = {
        "training": {
            "firstPress": first_press,
            "noteMs": 500,
            "trialMs": 700,
            "initial": [round(source["initial_weights"][i], 9) for i in changed],
            "final": [round(source["final_weights"][i], 9) for i in changed],
            "kcIds": kc_ids,
            "trials": trials,
        },
        "tests": tests,
        "sourceSha256": {
            "training": hashlib.sha256(TRAINING.read_bytes()).hexdigest(),
            "evaluation": hashlib.sha256(EVALUATION.read_bytes()).hexdigest(),
        },
    }
    html = TEMPLATE.read_text(encoding="utf-8")
    assert html.count("__EA_MVP_DATA__") == 1
    embedded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).replace("<", "\\u003c")
    OUTPUT.write_text(html.replace("__EA_MVP_DATA__", embedded), encoding="utf-8")
    print(f"Built {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")
    print(f"Training: {len(trials)} actual trials, first press {first_press}; tests: "
          + ", ".join(f"{tests[key]['title']} {len(tests[key]['notes'])} notes" for key, _ in PATTERNS))


if __name__ == "__main__":
    build()
