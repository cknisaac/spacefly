"""Plot the predeclared frozen-panel outcomes of the longitudinal study."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "docs/figures/long_continuation/result.json"
OUTPUT = ROOT / "docs/figures/long_continuation/probe_good.png"


def font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def main() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "complete"
    checkpoints = (24, 96, 384)
    conditions = ("on", "off", "shuffled")
    colors = {"on": (21, 111, 71), "off": (68, 92, 156),
              "shuffled": (192, 112, 38)}
    labels = {"on": "Plasticity on", "off": "Plasticity off",
              "shuffled": "Shuffled reward"}
    image = Image.new("RGB", (1200, 780), "white")
    draw = ImageDraw.Draw(image)
    left, right, top, bottom = 132, 1090, 135, 630

    def x(outcomes: int) -> int:
        return round(left + (outcomes - 24) / (384 - 24) * (right - left))

    def y(percent: float) -> int:
        return round(bottom - percent / 100 * (bottom - top))

    draw.text((left, 40), "Frozen performance after continued training",
              font=font(30, True), fill=(30, 36, 43))
    draw.text((left, 84), "Same network through 384 outcomes; fixed 32-note probe panel",
              font=font(19), fill=(77, 83, 90))
    for level in range(0, 101, 20):
        yy = y(level)
        draw.line((left, yy, right, yy), fill=(226, 230, 233), width=1)
        draw.text((left - 55, yy - 10), str(level), font=font(18),
                  fill=(80, 85, 91))
    for checkpoint in checkpoints:
        xx = x(checkpoint)
        draw.line((xx, bottom, xx, bottom + 8), fill=(70, 70, 70), width=2)
        draw.text((xx - 22, bottom + 17), str(checkpoint), font=font(18),
                  fill=(65, 70, 76))
    draw.line((left, top, left, bottom), fill=(65, 70, 76), width=2)
    draw.line((left, bottom, right, bottom), fill=(65, 70, 76), width=2)
    draw.text((left, bottom + 44), "Training outcomes retained per network",
              font=font(20), fill=(54, 59, 66))
    draw.text((left - 103, top - 37), "GOOD+ (%)", font=font(19),
              fill=(54, 59, 66))

    # Thin trajectories reveal heterogeneity; the bold series are cohort means.
    for condition in conditions:
        color = colors[condition]
        pale = tuple(round(0.76 * 255 + 0.24 * channel) for channel in color)
        for seed in result["seeds"]:
            values = [result["checkpoints"][str(c)]["conditions"][condition]
                      ["per_seed"][str(seed)]["good_or_better_percent"]
                      for c in checkpoints]
            points = [(x(c), y(v)) for c, v in zip(checkpoints, values)]
            draw.line(points, fill=pale, width=2)
            for px, py in points:
                draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=pale)
    for condition in conditions:
        values = [result["checkpoints"][str(c)]["conditions"][condition]
                  ["mean_good_or_better_percent"] for c in checkpoints]
        points = [(x(c), y(v)) for c, v in zip(checkpoints, values)]
        draw.line(points, fill=colors[condition], width=6)
        for px, py in points:
            draw.ellipse((px - 7, py - 7, px + 7, py + 7),
                         fill=colors[condition], outline="white", width=2)

    lx = left + 10
    for condition in conditions:
        draw.line((lx, 725, lx + 35, 725), fill=colors[condition], width=5)
        draw.text((lx + 46, 712), labels[condition], font=font(18),
                  fill=(54, 59, 66))
        lx += 290
    draw.text((left, 750), "Thin lines: all 8 paired seeds. Thick lines: mean. Descriptive diagnostic cohort.",
              font=font(15), fill=(97, 101, 107))
    image.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
