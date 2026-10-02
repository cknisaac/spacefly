"""A4 matched-parent manifest and fail-closed initial-state audit."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path

from project_b.checkpoint.codec import _canonical, _encode

from .controls import ControlPolicy
from .runtime import MvpSession


def digest(value) -> str:
    return hashlib.sha256(_canonical(_encode(value))).hexdigest()


def _allowed_paths(label: str, policy: ControlPolicy) -> list[str]:
    if label == "baseline":
        if policy != ControlPolicy():
            raise ValueError("baseline cannot change a control switch")
        return []
    switches = policy.active_switches()
    if len(switches) != 1:
        raise ValueError("A4 arm must change exactly one control switch")
    return ([f"identity.control_policy.{switches[0]}",
             f"state.control_policy.{switches[0]}"] +
            (["state.pam_router.teaching"] if policy.teaching == "wrong_note" else []) +
            (["state.plasticity.enabled"] if policy.plasticity == "off" else []))


def _differences(a, b, prefix: str = "") -> list[str]:
    if type(a) is dict and type(b) is dict:
        keys = sorted(set(a) | set(b))
        return [path for key in keys
                for path in _differences(a.get(key, object()), b.get(key, object()),
                                         f"{prefix}.{key}" if prefix else key)]
    if type(a) is list and type(b) is list:
        if len(a) != len(b):
            return [prefix + ".length"]
        return [path for i, (x, y) in enumerate(zip(a, b))
                for path in _differences(x, y, f"{prefix}[{i}]")]
    return [] if a == b else [prefix]


def create_manifest(parent: MvpSession, checkpoint_path: str,
                    checkpoint_state_sha256: str,
                    arms: dict[str, ControlPolicy]) -> dict:
    if (parent.controls != ControlPolicy() or parent.mode != "plastic" or
            not checkpoint_path or len(checkpoint_state_sha256) != 64 or
            not arms or "baseline" not in arms or arms["baseline"] != ControlPolicy()):
        raise ValueError("A4 manifest needs a baseline plastic parent checkpoint")
    for label, policy in arms.items():
        if not label or not isinstance(policy, ControlPolicy):
            raise ValueError("each A4 control must change exactly one declared switch")
        _allowed_paths(label, policy)
    state = parent.state()
    if digest(state) != checkpoint_state_sha256:
        raise ValueError("parent checkpoint state digest differs")
    return {
        "schema_id": "MVP-C1-A4-matched-parent-v1",
        "parent_checkpoint_path": checkpoint_path,
        "parent_checkpoint_state_sha256": checkpoint_state_sha256,
        "parent_identity": parent.identity,
        "parent_time_us": parent.time_us,
        "boundary_rng_states_sha256": digest(state["boundary"]["rng_states"]),
        "renderer_note_schedule_sha256": parent.identity["renderer_and_note_schedule_sha256"],
        "encoder_identity_sha256": digest(state["encoder"]["identity"]),
        "motor_identity_sha256": digest(state["motor"]["identity"]),
        "ruleset_and_metric_sha256": parent.identity["ruleset_and_metric_sha256"],
        "a3_metric_contract_sha256": hashlib.sha256((
            parent.root / "configs/a3_first_action_metric_contract.json").read_bytes()).hexdigest(),
        "arms": {name: {"control_policy": asdict(policy),
                        "allowed_start_differences": _allowed_paths(name, policy)}
                 for name, policy in arms.items()},
    }


def validate_pair_start(manifest: dict, parent: MvpSession,
                        label: str, arm: MvpSession) -> dict:
    """Reject undeclared differences; report exact field paths for diagnosis."""
    if (manifest.get("schema_id") != "MVP-C1-A4-matched-parent-v1" or
            label not in manifest.get("arms", {})):
        raise ValueError("A4 manifest schema or arm differs")
    parent_state, arm_state = parent.state(), arm.state()
    observed = []
    checkpoint_path = Path(manifest["parent_checkpoint_path"])
    if (not checkpoint_path.is_dir() or
            hashlib.sha256((checkpoint_path / "state.json").read_bytes()).hexdigest() !=
            manifest["parent_checkpoint_state_sha256"]):
        observed.append("parent_checkpoint_file_sha256")
    if digest(parent_state) != manifest["parent_checkpoint_state_sha256"]:
        observed.append("parent_checkpoint_state_sha256")
    if parent.identity != manifest["parent_identity"]:
        observed.extend("parent.identity." + x for x in
                        _differences(manifest["parent_identity"], parent.identity))
    if digest(parent_state["boundary"]["rng_states"]) != manifest["boundary_rng_states_sha256"]:
        observed.append("boundary_rng_states_sha256")
    if digest(parent_state["encoder"]["identity"]) != manifest["encoder_identity_sha256"]:
        observed.append("encoder_identity_sha256")
    if digest(parent_state["motor"]["identity"]) != manifest["motor_identity_sha256"]:
        observed.append("motor_identity_sha256")
    if hashlib.sha256((parent.root / "configs/a3_first_action_metric_contract.json")
                      .read_bytes()).hexdigest() != manifest["a3_metric_contract_sha256"]:
        observed.append("a3_metric_contract_sha256")
    expected_policy = manifest["arms"][label]["control_policy"]
    declared = ControlPolicy(**expected_policy)
    if manifest["arms"][label]["allowed_start_differences"] != _allowed_paths(label, declared):
        raise ValueError("A4 allowed-difference declaration differs from policy")
    if asdict(arm.controls) != expected_policy:
        observed.append("arm.control_policy")
    observed.extend("identity." + x for x in _differences(parent.identity, arm.identity))
    observed.extend("state." + x for x in _differences(parent_state, arm_state))
    allowed = set(manifest["arms"][label]["allowed_start_differences"])
    undeclared = sorted(set(observed) - allowed)
    receipt = {"arm": label, "parent_state_sha256": digest(parent_state),
               "arm_state_sha256": digest(arm_state),
               "observed_start_differences": sorted(set(observed)),
               "allowed_start_differences": sorted(allowed),
               "undeclared_start_differences": undeclared,
               "matched": not undeclared}
    if undeclared:
        raise ValueError("A4 undeclared start differences: " + ", ".join(undeclared[:12]))
    return receipt
