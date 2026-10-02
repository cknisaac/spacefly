"""Reproduce M1 voltage and tiny-circuit evidence from a fixed YAML config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator, VoltageSample
from project_b.synapses import SparseGraph, Synapse


def _spike_times(result, neuron: int) -> list[int]:
    return [event.time_us for event in result.spikes if event.neuron_index == neuron]


def _arrival_times(result) -> list[dict[str, int]]:
    return [{"time_us": event.time_us, "pre": event.pre, "post": event.post}
            for event in result.arrivals]


def build_report(config_path: Path) -> tuple[dict[str, object], tuple[VoltageSample, ...]]:
    """Run the declared examples; return machine-readable evidence and trace."""
    with config_path.open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    simulation = config["simulation"]
    model = config["model"]
    single = config["single_neuron"]
    circuits = config["circuits"]
    dt_us = simulation["dt_us"]
    single_params = LIFParameters(**model, refractory_us=single["refractory_us"])
    circuit_params = LIFParameters(**model, refractory_us=circuits["refractory_us"])
    single_sim = SpikingSimulator(
        [single_params], SparseGraph(1, []), [single["external_drive_mv"]],
        dt_us=dt_us, record_neurons=[0], record_spikes=True)
    single_result = single_sim.run_until(simulation["single_end_us"])

    def circuit(edges: list[Synapse], drives: list[float], end_us: int):
        simulator = SpikingSimulator(
            [circuit_params] * len(drives), SparseGraph(len(drives), edges), drives,
            dt_us=dt_us, record_neurons=range(len(drives)),
            record_spikes=True, record_arrivals=True)
        return simulator.run_until(end_us)

    weight_exc = circuits["excitatory_weight_mv"]
    weight_inh = circuits["inhibitory_weight_mv"]
    delay_us = circuits["delay_us"]
    drive_a = circuits["a_drive_mv"]
    drive_b = circuits["b_baseline_drive_mv"]
    end_us = simulation["circuit_end_us"]
    excited = circuit([Synapse(0, 1, weight_exc, delay_us)], [drive_a, 0.0], end_us)
    baseline = circuit([], [drive_a, drive_b], end_us)
    inhibited = circuit([Synapse(0, 1, weight_inh, delay_us)],
                        [drive_a, drive_b], end_us)
    chain = circuit([Synapse(0, 1, weight_exc, delay_us),
                     Synapse(1, 2, weight_exc, delay_us)],
                    [drive_a, 0.0, 0.0], end_us)
    off_grid = circuit([Synapse(0, 1, weight_exc, circuits["off_grid_delay_us"])],
                       [drive_a, 0.0], simulation["off_grid_end_us"])
    spike_samples = [sample for sample in single_result.voltage_trace if sample.spiked]
    report: dict[str, object] = {
        "config": config,
        "single_neuron": {
            "spike_times_us": _spike_times(single_result, 0),
            "threshold_crossing_and_reset": [
                {"time_us": sample.time_us,
                 "voltage_before_reset_mv": sample.voltage_before_reset_mv,
                 "voltage_after_reset_mv": sample.voltage_after_reset_mv,
                 "refractory_until_us": sample.refractory_until_us}
                for sample in spike_samples],
            "trace": [
                {"time_us": sample.time_us,
                 "voltage_before_reset_mv": sample.voltage_before_reset_mv,
                 "voltage_after_reset_mv": sample.voltage_after_reset_mv,
                 "spiked": sample.spiked}
                for sample in single_result.voltage_trace],
        },
        "excitation_a_to_b": {
            "a_spikes_us": _spike_times(excited, 0),
            "b_spikes_us": _spike_times(excited, 1),
            "arrivals": _arrival_times(excited),
        },
        "inhibition_a_to_b": {
            "a_spikes_us": _spike_times(inhibited, 0),
            "b_without_inhibition_us": _spike_times(baseline, 1),
            "b_with_inhibition_us": _spike_times(inhibited, 1),
            "arrivals": _arrival_times(inhibited),
        },
        "chain_a_to_b_to_c": {
            "a_spikes_us": _spike_times(chain, 0),
            "b_spikes_us": _spike_times(chain, 1),
            "c_spikes_us": _spike_times(chain, 2),
            "arrivals": _arrival_times(chain),
        },
        "off_grid_delay": {
            "a_spikes_us": _spike_times(off_grid, 0),
            "b_spikes_us": _spike_times(off_grid, 1),
            "arrivals": _arrival_times(off_grid),
        },
    }
    return report, single_result.voltage_trace


def draw_voltage_svg(trace: tuple[VoltageSample, ...], parameters: LIFParameters,
                     dt_us: int) -> str:
    """Make a standalone vector plot from the recorded, post-reset trace."""
    width, height = 980, 440
    left, right, top, bottom = 80, 30, 65, 65
    plot_w, plot_h = width - left - right, height - top - bottom
    max_time_us = trace[-1].time_us
    y_min, y_max = -0.08, max(1.28, parameters.v_threshold_mv * 1.25)

    def x(time_us: int) -> float:
        return left + time_us / max_time_us * plot_w

    def y(voltage_mv: float) -> float:
        return top + (y_max - voltage_mv) / (y_max - y_min) * plot_h

    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#fbfcfe"/>',
             '<text x="80" y="31" font-family="Arial,sans-serif" font-size="20" font-weight="bold" fill="#16253b">LIF membrane voltage under constant input</text>',
             f'<text x="80" y="51" font-family="Arial,sans-serif" font-size="12" fill="#526078">{dt_us/1000:g} ms integration ticks · spikes at threshold checks · {parameters.refractory_us/1000:g} ms refractory clamp</text>']
    for sample in trace:
        if sample.spiked and parameters.refractory_us:
            shade_x = x(sample.time_us)
            shade_w = x(min(sample.time_us + parameters.refractory_us, max_time_us)) - shade_x
            lines.append(f'<rect x="{shade_x:.2f}" y="{top}" width="{shade_w:.2f}" height="{plot_h}" fill="#e9edf4"/>')
    for tick_ms in range(0, max_time_us // 1000 + 1, 5):
        tick_x = x(tick_ms * 1000)
        lines.append(f'<line x1="{tick_x:.2f}" y1="{top}" x2="{tick_x:.2f}" y2="{top + plot_h}" stroke="#e5e9f0"/>')
        lines.append(f'<text x="{tick_x:.2f}" y="{top + plot_h + 23}" text-anchor="middle" font-family="Arial,sans-serif" font-size="12" fill="#48566b">{tick_ms}</text>')
    for tick_mv in (0.0, 0.5, 1.0):
        tick_y = y(tick_mv)
        lines.append(f'<line x1="{left}" y1="{tick_y:.2f}" x2="{left + plot_w}" y2="{tick_y:.2f}" stroke="#e5e9f0"/>')
        lines.append(f'<text x="{left - 13}" y="{tick_y + 4:.2f}" text-anchor="end" font-family="Arial,sans-serif" font-size="12" fill="#48566b">{tick_mv:.1f}</text>')
    threshold_y = y(parameters.v_threshold_mv)
    lines.append(f'<line x1="{left}" y1="{threshold_y:.2f}" x2="{left + plot_w}" y2="{threshold_y:.2f}" stroke="#c13a3a" stroke-width="2" stroke-dasharray="7 5"/>')
    lines.append(f'<text x="{left + plot_w - 5}" y="{threshold_y - 8:.2f}" text-anchor="end" font-family="Arial,sans-serif" font-size="12" fill="#b02f2f">threshold</text>')
    points = [(x(trace[0].time_us), y(trace[0].voltage_after_reset_mv))]
    for sample in trace[1:]:
        points.append((x(sample.time_us), y(sample.voltage_before_reset_mv)))
        if sample.spiked:
            points.append((x(sample.time_us), y(sample.voltage_after_reset_mv)))
    point_string = " ".join(f"{px:.2f},{py:.2f}" for px, py in points)
    lines.append(f'<polyline points="{point_string}" fill="none" stroke="#1769aa" stroke-width="3" stroke-linejoin="round"/>')
    for sample in trace:
        if sample.spiked:
            marker_x = x(sample.time_us)
            marker_y = y(sample.voltage_before_reset_mv)
            lines.append(f'<circle cx="{marker_x:.2f}" cy="{marker_y:.2f}" r="5" fill="#c13a3a"/>')
            lines.append(f'<text x="{marker_x:.2f}" y="{marker_y - 11:.2f}" text-anchor="middle" font-family="Arial,sans-serif" font-size="11" fill="#9f2828">SPIKE</text>')
    lines.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#37465c"/>')
    lines.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#37465c"/>')
    lines.append(f'<text x="{left + plot_w/2:.2f}" y="{height - 17}" text-anchor="middle" font-family="Arial,sans-serif" font-size="13" fill="#37465c">Time (ms)</text>')
    lines.append(f'<text transform="translate(25 {top + plot_h/2:.2f}) rotate(-90)" text-anchor="middle" font-family="Arial,sans-serif" font-size="13" fill="#37465c">Membrane voltage (mV)</text>')
    lines.append(f'<text x="{left + 15}" y="{top + 17}" font-family="Arial,sans-serif" font-size="11" fill="#526078">{escape("Blue: voltage rise/reset  ·  Grey: refractory  ·  Red: threshold/spikes")}</text>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def draw_voltage_png(trace: tuple[VoltageSample, ...], parameters: LIFParameters,
                     dt_us: int, path: Path) -> None:
    """Write a portable raster companion to the standalone SVG plot."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1400, 620
    left, right, top, bottom = 110, 55, 95, 90
    plot_w, plot_h = width - left - right, height - top - bottom
    max_time_us = trace[-1].time_us
    y_min, y_max = -0.08, max(1.28, parameters.v_threshold_mv * 1.25)

    def x(time_us: int) -> int:
        return round(left + time_us / max_time_us * plot_w)

    def y(voltage_mv: float) -> int:
        return round(top + (y_max - voltage_mv) / (y_max - y_min) * plot_h)

    def font(size: int):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            return ImageFont.load_default()

    picture = Image.new("RGB", (width, height), "#fbfcfe")
    draw = ImageDraw.Draw(picture)
    title_font, label_font, small_font = font(28), font(18), font(15)
    draw.text((left, 24), "LIF membrane voltage under constant input",
              fill="#16253b", font=title_font)
    draw.text((left, 62),
              f"{dt_us/1000:g} ms ticks · exact rise between events · {parameters.refractory_us/1000:g} ms refractory",
              fill="#526078", font=small_font)
    for sample in trace:
        if sample.spiked and parameters.refractory_us:
            draw.rectangle((x(sample.time_us), top,
                            x(min(sample.time_us + parameters.refractory_us,
                                  max_time_us)), top + plot_h), fill="#e9edf4")
    for tick_ms in range(0, max_time_us // 1000 + 1, 5):
        tick_x = x(tick_ms * 1000)
        draw.line((tick_x, top, tick_x, top + plot_h), fill="#e5e9f0", width=1)
        draw.text((tick_x - 10, top + plot_h + 16), str(tick_ms),
                  fill="#48566b", font=small_font)
    for tick_mv in (0.0, 0.5, 1.0):
        tick_y = y(tick_mv)
        draw.line((left, tick_y, left + plot_w, tick_y), fill="#e5e9f0", width=1)
        draw.text((left - 54, tick_y - 9), f"{tick_mv:.1f}",
                  fill="#48566b", font=small_font)
    threshold_y = y(parameters.v_threshold_mv)
    for dash_x in range(left, left + plot_w, 18):
        draw.line((dash_x, threshold_y, min(dash_x + 11, left + plot_w), threshold_y),
                  fill="#c13a3a", width=3)
    draw.text((left + plot_w - 335, threshold_y - 28), "threshold",
              fill="#a62c2c", font=small_font)
    points = [(x(trace[0].time_us), y(trace[0].voltage_after_reset_mv))]
    for sample in trace[1:]:
        points.append((x(sample.time_us), y(sample.voltage_before_reset_mv)))
        if sample.spiked:
            points.append((x(sample.time_us), y(sample.voltage_after_reset_mv)))
    draw.line(points, fill="#1769aa", width=4, joint="curve")
    for sample in trace:
        if sample.spiked:
            cx, cy = x(sample.time_us), y(sample.voltage_before_reset_mv)
            draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill="#c13a3a")
            draw.text((cx - 23, cy - 33), "SPIKE", fill="#9f2828", font=small_font)
    draw.line((left, top, left, top + plot_h, left + plot_w, top + plot_h),
              fill="#37465c", width=2)
    draw.text((left + plot_w // 2 - 45, height - 46), "Time (ms)",
              fill="#37465c", font=label_font)
    vertical_label = Image.new("RGBA", (220, 30), (0, 0, 0, 0))
    ImageDraw.Draw(vertical_label).text((0, 0), "Voltage (mV)",
                                        fill="#37465c", font=label_font)
    rotated_label = vertical_label.rotate(90, expand=True)
    picture.paste(rotated_label, (15, top + plot_h // 2 - 105), rotated_label)
    draw.text((left + 20, top + 15),
              "Blue: voltage rise/reset     Grey: refractory     Red: threshold/spikes",
              fill="#526078", font=small_font)
    picture.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/m1_demos.yaml"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/figures"))
    args = parser.parse_args()
    report, trace = build_report(args.config)
    with args.config.open("r", encoding="utf-8") as stream:
        settings = yaml.safe_load(stream)
    single_params = LIFParameters(
        **settings["model"],
        refractory_us=settings["single_neuron"]["refractory_us"])
    dt_us = settings["simulation"]["dt_us"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "m1_lif_trace.svg").write_text(
        draw_voltage_svg(trace, single_params, dt_us),
        encoding="utf-8")
    try:
        draw_voltage_png(trace, single_params, dt_us,
                         args.output_dir / "m1_lif_trace.png")
    except ImportError:
        print("Pillow unavailable; SVG remains the reproducible standalone plot")
    (args.output_dir / "m1_circuit_results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote M1 demonstration artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
