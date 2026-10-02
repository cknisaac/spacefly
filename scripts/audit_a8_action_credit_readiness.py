"""Independent AST and provenance audit of the A8 source-path result."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.a8_action_credit_readiness import FIRST_ACTION, OUT, PROTOCOL, ROOT, SOURCES, sha


def method(path: Path, class_name: str, method_name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method_name)


def calls_named(node: ast.AST, name: str) -> list[ast.Call]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == name]


def main() -> None:
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    historical = json.loads(FIRST_ACTION.read_text(encoding="utf-8"))
    historical_audit = json.loads((FIRST_ACTION.parent / "audit.json").read_text(encoding="utf-8"))
    assert result["protocol_sha256"] == sha(PROTOCOL)
    assert result["historical_first_action_result_sha256"] == sha(FIRST_ACTION)
    assert result["source_sha256"] == {
        str(path.relative_to(ROOT)): sha(path) for path in SOURCES.values()}
    assert protocol["stage"] == result["stage"] == "A8"
    assert historical["status"] == "complete" and historical_audit["status"] == "passed"
    assert (result["historical_frozen_good_plus"],
            result["historical_good_plus_after_null"]) == (
                historical["aggregate"]["frozen_good_plus_count"],
                historical["aggregate"]["good_plus_after_same_note_null_count"]) == (236, 233)
    step = method(SOURCES["session"], "TinyLaneSession", "step")
    reward_calls = calls_named(step, "process_judgement")
    assert len(reward_calls) == 1
    reward_for = [n for n in ast.walk(step) if isinstance(n, ast.For)
                  and reward_calls[0] in ast.walk(n)]
    assert len(reward_for) == 1
    assert "newly_judged" in ast.unparse(reward_for[0].iter)
    action_calls = calls_named(step, "apply_action")
    assert len(action_calls) == 1
    assert action_calls[0].lineno < reward_calls[0].lineno
    motor_drive = [n for n in ast.walk(step) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Subscript)
                           and ast.unparse(t) == "drive[cell]" for t in n.targets)]
    assert len(motor_drive) == 1 and ast.literal_eval(motor_drive[0].value) == 20.0
    motor_loops = [n for n in ast.walk(step) if isinstance(n, ast.For)
                   and motor_drive[0] in ast.walk(n)]
    assert len(motor_loops) == 1 and ast.unparse(motor_loops[0].iter) == "self.layout.motor"
    plastic = method(SOURCES["eligibility"], "ThreeFactorPlasticity", "apply_dopamine")
    assert len([n for n in ast.walk(plastic) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "proposed" for t in n.targets)
                and ast.unparse(n.value) ==
                "previous + self.parameters.eta * eligibility * dopamine"]) == 1
    assert result["design_readiness"] == "FAIL_CURRENT_SIGNAL_PATH"
    receipt = {
        "status": "passed",
        "stage": "A8",
        "source_ast_checked": len(SOURCES),
        "judgement_gated_reward_calls": len(reward_calls),
        "single_shared_positive_motor_drive_assignment": True,
        "historical_first_action_audit_passed": True,
        "protocol_sha256": sha(PROTOCOL),
        "result_sha256": sha(OUT / "result.json"),
    }
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
