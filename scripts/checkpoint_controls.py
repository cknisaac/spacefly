"""Predeclared synthetic reward-control sweep. Run from the project root.

This tests the fixture's ability to learn, not fly connectome behavior.
"""

from __future__ import annotations

import json
import hashlib
import random
import subprocess
import sys
from dataclasses import asdict
from dataclasses import replace
from pathlib import Path

from project_b.experiments import TinyBrainConfig, run_tiny_lane_one
from project_b.osu import ManiaJudgement

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "configs" / "checkpoint_controls.json"
FIGURES = ROOT / "docs" / "figures"
COLORS = {"on": "#1876ad", "off": "#a66b27", "shuffled": "#a24070"}
NAMES = {"on": "Plasticity on", "off": "Plasticity off",
         "shuffled": "Shuffled reward"}


def provenance() -> dict:
    sources = (
        "src/project_b/experiments/tiny_brain.py",
        "src/project_b/neuromodulation/reward.py",
        "src/project_b/plasticity/eligibility.py",
        "src/project_b/sensory/time_to_contact.py",
        "src/project_b/motor/fixed_readout.py",
    )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
        text=True, check=False)
    return {
        "python": sys.version.split()[0],
        "git_commit": revision.stdout.strip() if revision.returncode == 0 else None,
        "synthetic_topology": "build_tiny_brain; no imported connectome",
        "source_sha256": {
            source: hashlib.sha256((ROOT/source).read_bytes()).hexdigest()
            for source in sources},
    }


def shuffled_utilities(values: tuple[float, ...], seed: int) -> tuple[float, ...]:
    """Deterministic permutation of a recorded training reward multiset."""
    shuffled = list(values)
    random.Random(seed ^ 0x5A17B53D).shuffle(shuffled)
    if len(set(values)) > 1 and tuple(shuffled) == values:
        shuffled = list(values[1:] + values[:1])
    assert sorted(shuffled) == sorted(values)
    return tuple(shuffled)


def summarize(result, train_count: int) -> dict:
    records = []
    for index, (judgement, feedback) in enumerate(zip(result.judgements, result.feedback)):
        records.append({
            "note_index": index,
            "phase": "training" if index < train_count else "frozen",
            "judgement": judgement.judgement.name,
            "hit_value": int(judgement.judgement),
            "hit_error_us": judgement.hit_error_us,
            "game_utility": feedback.reinforcement.utility.utility,
            "learning_utility": feedback.reinforcement.learning_utility,
            "rpe": feedback.reinforcement.prediction.rpe,
            "dopamine_like_amplitude": feedback.reinforcement.modulation.amplitude,
            "weight_changes": len(feedback.weight_changes),
        })
    frozen = records[train_count:]
    hits = [r for r in frozen if r["judgement"] != ManiaJudgement.MISS.name]
    good = [r for r in frozen if r["hit_value"] >= 200]
    return {
        "frozen_non_miss_percent": 100 * len(hits) / len(frozen),
        "frozen_good_or_better_percent": 100 * len(good) / len(frozen),
        "frozen_mean_hit_value": sum(r["hit_value"] for r in frozen) / len(frozen),
        "frozen_mean_absolute_error_ms": (
            sum(abs(r["hit_error_us"]) for r in hits) / len(hits) / 1000
            if hits else None),
        "frozen_early_ok_count": sum(
            r["judgement"] == ManiaJudgement.OK_100.name
            and r["hit_error_us"] is not None and r["hit_error_us"] < 0
            for r in frozen),
        "training_hits_by_note": [int(r["judgement"] != ManiaJudgement.MISS.name)
                                  for r in records[:train_count]],
        "final_weight_change_count": sum(
            a != b for a, b in zip(result.initial_plastic_weights_mv,
                                   result.final_plastic_weights_mv)),
        "events": records,
    }


def font(size: int, bold: bool = False):
    from PIL import ImageFont

    stem = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / stem), size)


def draw_plot(report: dict, path: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1500, 850), "#ffffff")
    d = ImageDraw.Draw(image)
    f_title, f_sub = font(40, True), font(22)
    f_label, f_small = font(23, True), font(19)
    d.text((80, 35), "Synthetic lane-one learning checkpoint", fill="#182939", font=f_title)
    d.text((80, 90), "16 declared seeds · 8 training notes · 8 frozen notes per seed",
           fill="#526477", font=f_sub)
    # Left: cumulative training hit rate. This is descriptive; training uses exploration.
    x0, y0, x1, y1 = 105, 180, 810, 675
    for value in range(0, 101, 20):
        y = y1 - (y1-y0)*value/100
        d.line((x0, y, x1, y), fill="#e6ebef", width=2)
        d.text((42, y-12), f"{value}", fill="#566675", font=f_small)
    d.line((x0, y0, x0, y1), fill="#536679", width=3)
    d.line((x0, y1, x1, y1), fill="#536679", width=3)
    d.text((105, 140), "Training cumulative hit rate (%)", fill="#182939", font=f_label)
    d.text((355, 710), "Training notes seen", fill="#526477", font=f_sub)
    ntrain = report["config"]["training_notes"]
    for k in range(1, ntrain+1):
        x = x0+(x1-x0)*(k-1)/(ntrain-1)
        d.text((x-6, y1+15), str(k), fill="#526477", font=f_small)
    for condition in ("off", "shuffled", "on"):
        means = []
        for k in range(1, ntrain+1):
            means.append(sum(sum(seed[condition]["training_hits_by_note"][:k])/k
                             for seed in report["seeds"]) / len(report["seeds"]) * 100)
        pts = [(x0+(x1-x0)*i/(ntrain-1), y1-(y1-y0)*v/100)
               for i, v in enumerate(means)]
        d.line(pts, fill=COLORS[condition], width=5, joint="curve")
        for x, y in pts:
            d.ellipse((x-5, y-5, x+5, y+5), fill=COLORS[condition])
    # Right: paired frozen performance for every seed, plus mean bars.
    rx0, ry0, rx1, ry1 = 920, 180, 1430, 675
    d.text((920, 140), "Frozen hit rate by seed (%)", fill="#182939", font=f_label)
    for value in range(0, 101, 20):
        y = ry1-(ry1-ry0)*value/100
        d.line((rx0, y, rx1, y), fill="#e6ebef", width=2)
        d.text((863, y-12), f"{value}", fill="#566675", font=f_small)
    centers = {"on": 995, "off": 1165, "shuffled": 1335}
    for condition, cx in centers.items():
        vals = [seed[condition]["frozen_non_miss_percent"] for seed in report["seeds"]]
        mean = sum(vals)/len(vals)
        y = ry1-(ry1-ry0)*mean/100
        d.rectangle((cx-36, y, cx+36, ry1), fill=COLORS[condition])
        for i, value in enumerate(vals):
            px = cx-25+(i%8)*7
            py = ry1-(ry1-ry0)*value/100
            d.ellipse((px-4, py-4, px+4, py+4), fill="#152634")
        d.text((cx-32, max(ry0, y-31)), f"{mean:.1f}%", fill=COLORS[condition],
               font=f_label)
        label = {"on": "On", "off": "Off", "shuffled": "Shuffled"}[condition]
        d.text((cx-47, ry1+15), label, fill="#526477", font=f_small)
    ly = 780
    for condition, lx in (("on", 250), ("off", 610), ("shuffled", 950)):
        d.line((lx, ly, lx+45, ly), fill=COLORS[condition], width=6)
        d.text((lx+58, ly-13), NAMES[condition], fill="#253746", font=f_sub)
    d.text((80, 820), "Hit = non-MISS. Each dot = one seed; bars = mean. Frozen evaluation has no exploration or weight updates.",
           fill="#566675", font=font(16))
    image.save(path)


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    train = spec["training_notes"]
    count = train + spec["frozen_notes"]
    rows = []
    for seed in spec["seeds"]:
        base = TinyBrainConfig(note_count=count, training_notes=train, seed=seed,
                               first_note_us=spec["first_note_us"],
                               note_interval_us=spec["note_interval_us"])
        on = run_tiny_lane_one(base)
        off = run_tiny_lane_one(replace(base, plasticity_enabled=False))
        utilities = tuple(f.reinforcement.utility.utility for f in on.feedback[:train])
        shuffled = shuffled_utilities(utilities, seed)
        control = run_tiny_lane_one(replace(base, reward_utility_schedule=shuffled))
        rows.append({"seed": seed, "resolved_base_config": asdict(base),
                     "on": summarize(on, train),
                     "off": summarize(off, train),
                     "shuffled": summarize(control, train),
                     "on_training_utilities": utilities,
                     "shuffled_training_utilities": shuffled,
                     "permutation_changed": utilities != shuffled})
        print(f"seed {seed:02d}: frozen hits on/off/shuffled = "
              f"{rows[-1]['on']['frozen_non_miss_percent']:.0f}/"
              f"{rows[-1]['off']['frozen_non_miss_percent']:.0f}/"
              f"{rows[-1]['shuffled']['frozen_non_miss_percent']:.0f}%", flush=True)
    summary = {}
    for condition in NAMES:
        summary[condition] = {
            metric: sum(row[condition][metric] for row in rows)/len(rows)
            for metric in ("frozen_non_miss_percent", "frozen_good_or_better_percent",
                           "frozen_mean_hit_value", "frozen_early_ok_count")}
    primary = "frozen_non_miss_percent"
    gate = spec["reliability_gate"]
    comparisons = {}
    for control in ("off", "shuffled"):
        differences = [row["on"][primary]-row[control][primary] for row in rows]
        comparisons[control] = {
            "mean_paired_advantage_percentage_points": sum(differences)/len(differences),
            "strict_win_seeds": sum(d > 0 for d in differences),
            "tie_seeds": sum(d == 0 for d in differences),
            "strict_loss_seeds": sum(d < 0 for d in differences),
            "passes_declared_gate": (
                sum(differences)/len(differences)
                >= gate["minimum_mean_paired_advantage_percentage_points_vs_each_control"]
                and sum(d > 0 for d in differences)
                >= gate["minimum_seeds_strictly_above_each_control"]),
        }
    report = {"config": spec, "provenance": provenance(),
              "summary": summary, "comparisons": comparisons,
              "overall_reliability_gate_passes": all(
                  c["passes_declared_gate"] for c in comparisons.values()),
              "seeds": rows,
              "limitations": [
                  "One fixed, evenly spaced synthetic lane-one map is used for both phases.",
                  "Training hit rates include exploratory motor stimulation and are descriptive only.",
                  "The shuffled control uses an offline on-policy reward multiset; its reward sequence is not causal feedback from its own performance.",
                  "Non-MISS hits include early OK; precision and transfer must be assessed separately.",
              ]}
    FIGURES.mkdir(parents=True, exist_ok=True)
    json_path = FIGURES / "checkpoint_controls.json"
    png_path = FIGURES / "checkpoint_controls.png"
    json_path.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    draw_plot(report, png_path)
    print(json.dumps({"summary": summary, "comparisons": comparisons,
                      "overall_reliability_gate_passes": report["overall_reliability_gate_passes"],
                      "reward_permutations_changed": sum(row["permutation_changed"] for row in rows)},
                     indent=2), flush=True)
    print(f"wrote {json_path} and {png_path}", flush=True)


if __name__ == "__main__":
    main()
