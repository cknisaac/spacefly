"""Plot the completed overnight study from its immutable per-run ledger."""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "figures" / "overnight_synthetic"
COLORS = {"on": "#1976af", "off": "#a36b27", "shuffled": "#a44372"}


def font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def plot(path: Path = DATA / "summary.png") -> None:
    result = json.loads((DATA / "result.json").read_text(encoding="utf-8"))
    if result["status"] != "complete" or result["completed_runs"] != result["planned_runs"]:
        raise ValueError("the study is not complete")
    rows = [json.loads(line) for line in (DATA / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(rows) != result["planned_runs"] or len({r["key"] for r in rows}) != len(rows):
        raise ValueError("incomplete or duplicate ledger")
    selected = result["gate"]["selected_threshold"]
    image = Image.new("RGB", (1600, 980), "white")
    d = ImageDraw.Draw(image)
    d.text((75, 32), "Synthetic timing gate: held-out result", font=font(42, True), fill="#172b3d")
    d.text((75, 91), "32 development seeds · 32 held-out seeds · 24 training + 16 frozen notes",
           font=font(24), fill="#506476")
    d.rounded_rectangle((1285, 42, 1510, 106), radius=15, fill="#f9e8e8")
    d.text((1320, 58), "GATE FAILED", font=font(26, True), fill="#a53838")

    # Development selection panel.
    lx0, lx1, ly0, ly1 = 95, 700, 205, 625
    d.text((95, 158), "Development: frozen GOOD+ (%)", font=font(25, True), fill="#172b3d")
    for value in range(0, 101, 20):
        y = ly1 - (ly1-ly0)*value/100
        d.line((lx0, y, lx1, y), fill="#e5ebef", width=2)
        d.text((40, y-11), str(value), font=font(17), fill="#526779")
    for threshold, x in ((6, 235), (8, 405), (10, 575)):
        values = [r["summary"]["frozen_good_or_better_percent"] for r in rows
                  if r["stage"] == "dev" and r["threshold"] == threshold]
        mean = statistics.mean(values)
        y = ly1 - (ly1-ly0)*mean/100
        d.rectangle((x-45, y, x+45, ly1), fill="#8ca8bc" if threshold != selected else COLORS["on"])
        for index, value in enumerate(values):
            px = x-31+(index%8)*9
            py = ly1-(ly1-ly0)*value/100
            d.ellipse((px-3, py-3, px+3, py+3), fill="#1c2f3b")
        d.text((x-42, max(ly0, y-34)), f"{mean:.1f}%", font=font(22, True),
               fill=COLORS["on"] if threshold == selected else "#556b7d")
        d.text((x-44, ly1+13), f"T={threshold}", font=font(22), fill="#526779")
    d.text((155, 681), f"Threshold {selected} selected using development seeds only",
           font=font(19), fill="#526779")

    # Held-out three-condition panel.
    rx0, rx1, ry0, ry1 = 855, 1515, 205, 625
    d.text((855, 158), "Held-out: frozen GOOD+ (%)", font=font(25, True), fill="#172b3d")
    for value in range(0, 101, 20):
        y = ry1-(ry1-ry0)*value/100
        d.line((rx0, y, rx1, y), fill="#e5ebef", width=2)
        d.text((803, y-11), str(value), font=font(17), fill="#526779")
    for condition, x, label in (("on", 965, "On"), ("off", 1180, "Off"),
                                ("shuffled", 1395, "Shuffled")):
        values = [r["summary"]["frozen_good_or_better_percent"] for r in rows
                  if r["stage"] == "heldout" and r["condition"] == condition]
        mean = statistics.mean(values)
        y = ry1-(ry1-ry0)*mean/100
        d.rectangle((x-49, y, x+49, ry1), fill=COLORS[condition])
        for index, value in enumerate(values):
            px = x-35+(index%8)*10
            py = ry1-(ry1-ry0)*value/100
            d.ellipse((px-3, py-3, px+3, py+3), fill="#1c2f3b")
        d.text((x-43, max(ry0, y-34)), f"{mean:.1f}%", font=font(22, True),
               fill=COLORS[condition])
        d.text((x-52, ry1+13), label, font=font(22), fill="#526779")
    d.text((872, 681), "Strict seed wins: on > off 16/32; on > shuffle 15/32",
           font=font(19), fill="#526779")

    # Signed press-error histogram for the on condition's non-MISS frozen hits.
    errors = [e["hit_error_us"]/1000 for r in rows
              if r["stage"] == "heldout" and r["condition"] == "on"
              for e in r["summary"]["events"]
              if e["phase"] == "frozen" and e["judgement"] != "MISS"
              and e["hit_error_us"] is not None]
    bins = list(range(-170, 171, 20))
    counts = Counter(max(0, min(len(bins)-2, int((error+170)//20))) for error in errors)
    d.text((95, 742), "Plasticity-on frozen hit timing (signed error, ms)",
           font=font(25, True), fill="#172b3d")
    hx0, hx1, hy0, hy1 = 100, 1510, 790, 905
    maximum = max(counts.values()) if counts else 1
    for i in range(len(bins)-1):
        x0 = hx0+(hx1-hx0)*i/(len(bins)-1)
        x1 = hx0+(hx1-hx0)*(i+1)/(len(bins)-1)
        height = (hy1-hy0)*counts[i]/maximum
        d.rectangle((x0+2, hy1-height, x1-2, hy1), fill=COLORS["on"])
    zero_x = hx0+(hx1-hx0)*170/340
    d.line((zero_x, hy0, zero_x, hy1), fill="#ad3441", width=3)
    d.text((zero_x+6, hy0), "note time", font=font(17), fill="#ad3441")
    for tick in (-160, -120, -80, -40, 0, 40, 80, 120, 160):
        x = hx0+(hx1-hx0)*(tick+170)/340
        d.text((x-20, hy1+8), str(tick), font=font(16), fill="#526779")
    d.text((95, 947), "Dots = seeds, bars = means. Frozen phase has no exploration or weight updates. "
           "GOOD+ includes 200, 300 and MAX; the declared seed gate and 40 ms timing limit failed.",
           font=font(17), fill="#526779")
    image.save(path)


if __name__ == "__main__":
    plot()
