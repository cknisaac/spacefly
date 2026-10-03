"""Independently reconstruct EA-3.1 first DOWNs and source identities."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_no_cue_output_protocol.json"
RESULT = ROOT / "runs/ea_mvp/no_cue_output.json"


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["protocol_sha256"] == hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    config_path = ROOT / protocol["source_config"]
    assert result["source_config_sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    sources = {cell["source_id"] for cell in config["circuit"]["selected_kcs"]}
    sources.add(config["circuit"]["mbon_source_id"])
    checked = 0
    for name, arm in result["arms"].items():
        record = arm["record"]
        if name == "no_cue":
            assert not record["spikes"] and not record["arrivals"]
            continue
        downs = [row["episode_time_us"] for row in record["actions"]
                 if row["kind"] == "down"]
        assert record["first_down_us"] == (downs[0] if downs else None)
        assert all(row["source_id"] in sources for row in record["source_tagged_spikes"])
        assert all(row["pre_source_id"] in sources and row["post_source_id"] in sources
                   for row in record["source_tagged_arrivals"])
        assert record["queued_arrivals"] >= 0
        checked += 1
    assert result["status"] == "PASS" and all(result["checks"].values())
    print(f"PASS: independently audited first DOWN and source IDs in {checked} cue arms")


if __name__ == "__main__":
    main()
