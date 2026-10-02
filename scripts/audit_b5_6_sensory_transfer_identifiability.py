"""Structural/provenance audit of B5.6's literature decision, without simulation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/b5_6_sensory_transfer_identifiability.json"
LEDGER = ROOT / "docs/figures/b5_6_sensory_transfer_identifiability/evidence_ledger.json"
OUTPUT = LEDGER.parent / "audit.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    checks["stage_and_locked_question"] = (
        protocol["stage_id"] == ledger["stage"] == "B5.6"
        and "jointly bound" in protocol["question"]
    )
    pinned = protocol["locked_evidence_sha256"]
    for name, expected in pinned.items():
        folder = "configs" if name.endswith(".json") and name.startswith("electrical_model") else "docs"
        if name == "b5_5_audit.json":
            file = ROOT / "docs/figures/b5_5_visual_kc_transfer_decomposition/audit.json"
        else:
            file = ROOT / folder / name
        checks[f"pinned_{name}"] = file.is_file() and sha256(file) == expected
    sources = ledger["sources"]
    checks["unique_primary_sources"] = len(sources) == len({row["doi"] for row in sources}) and len(sources) >= 4
    required = {
        "id", "title", "url", "doi", "source_type", "review_status", "preparation",
        "measurement", "units_or_readout", "what_it_constrains", "what_it_does_not_measure",
        "class_match", "source_specific_transfer", "matched_intrinsic",
        "joint_numerical_envelope", "classification",
    }
    checks["ledger_fields_complete"] = all(required <= row.keys() for row in sources)
    checks["primary_citations_present"] = all(
        row["url"].startswith("https://") and row["doi"] and "primary" in row["source_type"]
        for row in sources
    )
    checks["joint_rule_applied_consistently"] = all(
        not row["joint_numerical_envelope"]
        or (row["class_match"] and row["source_specific_transfer"] and row["matched_intrinsic"])
        for row in sources
    )
    any_joint = any(row["joint_numerical_envelope"] for row in sources)
    checks["decision_matches_ledger"] = ledger["decision"]["joint_envelope_identified"] == any_joint
    checks["no_unjustified_revision"] = (
        not any_joint and not ledger["decision"]["production_revision_authorized"]
    )
    checks["anatomy_not_miscast_as_physiology"] = (
        ledger["local_measured_anatomy"]["classification"] == "MEASURED"
        and not ledger["local_measured_anatomy"]["physiological_inference_allowed"]
    )
    checks["no_diagnostic_number_used_to_calibrate"] = ledger["criteria"]["no_simulator_derived_numbers"]
    audit = {
        "stage": "B5.6",
        "audit_scope": "Independent structural/provenance checks; source-content interpretation remains a literature judgment, not machine verification",
        "protocol_sha256": sha256(PROTOCOL),
        "ledger_sha256": sha256(LEDGER),
        "sources_checked": len(sources),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    OUTPUT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    if audit["status"] != "PASS":
        raise SystemExit(json.dumps(audit, indent=2))
    print(json.dumps({"status": audit["status"], "sources_checked": len(sources), "checks": len(checks)}))


if __name__ == "__main__":
    main()
