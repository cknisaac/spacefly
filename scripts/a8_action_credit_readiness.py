"""Source-backed A8 information-path audit; does not execute a training run."""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a8_action_credit_readiness.json"
FIRST_ACTION = ROOT / "docs/figures/heldout_first_action_audit/result.json"
OUT = ROOT / "docs/figures/a8_action_credit_readiness"
SOURCES = {
    "session": ROOT / "src/project_b/experiments/tiny_brain.py",
    "eligibility": ROOT / "src/project_b/plasticity/eligibility.py",
    "readout": ROOT / "src/project_b/motor/fixed_readout.py",
    "reward": ROOT / "src/project_b/neuromodulation/reward.py",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def line_with(source: str, fragment: str) -> int:
    matches = [i for i, line in enumerate(source.splitlines(), 1) if fragment in line]
    if len(matches) != 1:
        raise AssertionError((fragment, matches))
    return matches[0]


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["stage"] == "A8"
    sources = {name: path.read_text(encoding="utf-8") for name, path in SOURCES.items()}
    for source in sources.values():
        ast.parse(source)
    s, p, r = (sources[name] for name in ("session", "eligibility", "reward"))
    facts = {
        "exploration_is_one_shared_positive_motor_pulse": {
            "source": str(SOURCES["session"].relative_to(ROOT)),
            "rng_draw_line": line_with(s, "self.rng.random() < self.config.exploration_probability"),
            "all_motor_loop_line": line_with(s, "for cell in self.layout.motor:"),
            "positive_drive_line": line_with(s, "drive[cell] = 20.0"),
            "independent_signed_per_motor_perturbation_present": False,
        },
        "feedback_is_generated_from_new_judgements_only": {
            "source": str(SOURCES["session"].relative_to(ROOT)),
            "action_line": line_with(s, "self.game.apply_action(decision.action)"),
            "judgement_slice_line": line_with(s, "newly_judged = self.game.result().judgements[self.resolved_count:]"),
            "reward_loop_line": line_with(s, "for offset, judgement in enumerate(newly_judged):"),
            "reward_call_line": line_with(s, "event = self.reward.process_judgement("),
            "null_down_reward_call_present": False,
        },
        "plasticity_has_nonnegative_pairs_and_scalar_modulator": {
            "source": str(SOURCES["eligibility"].relative_to(ROOT)),
            "pre_increment_line": line_with(p, "updated = pre_value + 1.0"),
            "eligibility_increment_line": line_with(p, "updated = eligibility + pre_value"),
            "scalar_update_line": line_with(p, "proposed = previous + self.parameters.eta * eligibility * dopamine"),
            "action_identity_in_plasticity_state": False,
        },
        "reward_translates_resolved_judgement": {
            "source": str(SOURCES["reward"].relative_to(ROOT)),
            "translator_line": line_with(r, "translated = self.utility.translate(record.judgement)"),
        },
    }
    aggregate = json.loads(FIRST_ACTION.read_text(encoding="utf-8"))["aggregate"]
    assert aggregate["frozen_good_plus_count"] == 236
    assert aggregate["good_plus_after_same_note_null_count"] == 233
    result = {
        "status": "complete",
        "stage": "A8",
        "design_readiness": "FAIL_CURRENT_SIGNAL_PATH",
        "protocol_sha256": sha(PROTOCOL),
        "historical_first_action_result_sha256": sha(FIRST_ACTION),
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in SOURCES.values()},
        "facts": facts,
        "historical_frozen_good_plus": aggregate["frozen_good_plus_count"],
        "historical_good_plus_after_null": aggregate["good_plus_after_same_note_null_count"],
        "interfaces_missing_for_the_proposed_signed_first_action_rule": [
            "causal first-action feedback boundary, including null DOWN",
            "signed local causal perturbation or eligibility term that can attribute earlier/later motor effects",
        ],
        "scope": "source and historical-data audit only; no new training, probe or corrected-rule result",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage": result["stage"], "design_readiness": result["design_readiness"],
                      "source_count": len(SOURCES),
                      "historical_good_plus_after_null": result["historical_good_plus_after_null"]}))


if __name__ == "__main__":
    main()
