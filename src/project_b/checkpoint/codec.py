"""Exact finite-binary64 JSON bundle for committed MVP state owners."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from enum import Enum
from pathlib import Path


SCHEMA_ID = "A2-component-checkpoint-v0"
BOUNDARY = "COMMITTED_TICK_AFTER_FEEDBACK_AND_LEDGER_FLUSH"
INT64_MIN, INT64_MAX = -(2**63), 2**63 - 1


def _encode(value):
    if isinstance(value, Enum):
        return _encode(value.value)
    if value is None or type(value) in (str, bool):
        return value
    if type(value) is int:
        if not INT64_MIN <= value <= INT64_MAX:
            raise ValueError("checkpoint integer outside signed 64-bit range")
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("checkpoint contains a non-finite float")
        return {"__binary64_hex__": value.hex()}
    if isinstance(value, (list, tuple)):
        return [_encode(v) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        if "__binary64_hex__" in value:
            raise ValueError("reserved checkpoint field")
        return {k: _encode(v) for k, v in value.items()}
    raise TypeError(f"unsupported checkpoint value type: {type(value).__name__}")


def _decode(value):
    if type(value) is dict and set(value) == {"__binary64_hex__"}:
        raw = value["__binary64_hex__"]
        if type(raw) is not str:
            raise ValueError("invalid binary64 encoding")
        number = float.fromhex(raw)
        if not math.isfinite(number) or number.hex() != raw:
            raise ValueError("noncanonical or non-finite binary64 encoding")
        return number
    if type(value) is dict:
        if "__binary64_hex__" in value:
            raise ValueError("invalid binary64 wrapper")
        return {k: _decode(v) for k, v in value.items()}
    if type(value) is list:
        return [_decode(v) for v in value]
    if type(value) is int and not INT64_MIN <= value <= INT64_MAX:
        raise ValueError("checkpoint integer outside signed 64-bit range")
    if value is None or type(value) in (str, bool, int):
        return value
    raise ValueError("invalid checkpoint JSON value")


def _canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate checkpoint JSON field")
        result[key] = value
    return result


def save_checkpoint(path: Path, identity: dict, state: dict, *,
                    schema_id: str = SCHEMA_ID) -> str:
    """Write a new two-file bundle atomically; never overwrite a checkpoint."""
    target = Path(path)
    if schema_id not in (SCHEMA_ID, "MVP-C1-checkpoint-v1"):
        raise ValueError("unsupported checkpoint schema")
    if target.exists() or not target.parent.is_dir():
        raise ValueError("checkpoint target must be new under an existing directory")
    if state.get("phase") != BOUNDARY or type(state.get("time_us")) is not int:
        raise ValueError("checkpoint requires a committed tick")
    if not isinstance(identity, dict) or not identity:
        raise ValueError("checkpoint identity is required")
    body = _canonical(_encode(state))
    digest = hashlib.sha256(body).hexdigest()
    manifest = _canonical({"schema_id": schema_id, "boundary": BOUNDARY,
                           "identity": _encode(identity), "state_sha256": digest})
    with tempfile.TemporaryDirectory(prefix=".checkpoint-", dir=target.parent) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir()
        for name, payload in (("state.json", body), ("manifest.json", manifest)):
            with (staging / name).open("wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        os.replace(staging, target)
    return digest


def load_checkpoint(path: Path, expected_identity: dict, *,
                    schema_id: str = SCHEMA_ID) -> dict:
    """Verify exact schema, identity, checksum and canonical encoding."""
    target = Path(path)
    manifest_bytes = (target / "manifest.json").read_bytes()
    state_bytes = (target / "state.json").read_bytes()
    manifest = json.loads(manifest_bytes, object_pairs_hook=_strict_pairs)
    if (set(manifest) != {"schema_id", "boundary", "identity", "state_sha256"}
            or manifest["schema_id"] != schema_id or manifest["boundary"] != BOUNDARY
            or _decode(manifest["identity"]) != expected_identity
            or manifest_bytes != _canonical(manifest)
            or hashlib.sha256(state_bytes).hexdigest() != manifest["state_sha256"]):
        raise ValueError("checkpoint schema, identity or checksum differs")
    encoded = json.loads(state_bytes, object_pairs_hook=_strict_pairs)
    if state_bytes != _canonical(encoded):
        raise ValueError("checkpoint state is not canonical")
    state = _decode(encoded)
    if state.get("phase") != BOUNDARY or type(state.get("time_us")) is not int:
        raise ValueError("checkpoint is not at the committed tick boundary")
    return state
