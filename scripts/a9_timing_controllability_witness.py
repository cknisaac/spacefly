"""One hand-specified cue-class weight witness; no learning or search."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from project_b.osu import GameEnvironment
from scripts.a8_2_first_action_local_direction import OUT as A82_OUT, norm
from scripts.cue_300ms_necessity_diagnostic import probe_with_readout_trace
from scripts.cue_300ms_saturation_contrast_diagnostic import first_note
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.long_continuation import atomic_json, sha
from scripts.successive_update_interference_diagnostic import timing_summary


ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"configs/a9_timing_controllability_witness.json"
A5=ROOT/"docs/figures/cue_300ms_necessity"
OUT=ROOT/"docs/figures/a9_timing_controllability_witness"
EARLY=(500_000,400_000,300_000,200_000)


def note_actions(probe:dict) -> list[dict]:
    times=[probe["checkpoint_time_us"]+x for x in probe["relative_note_offsets_us"]]
    expiry_offset_us=GameEnvironment(()).windows.expiry_offset_us
    rows=[]
    for i,t in enumerate(times):
        downs=[a for a in probe["down_actions"]
               if t-500_000<=a["time_us"]<=t+expiry_offset_us]
        first=downs[0] if downs else None
        event=probe["events"][i]
        rows.append({"note_index":i,"note_time_us":t,"first_down":first,
                     "first_down_offset_us":first["time_us"]-t if first else None,
                     "down_count":len(downs),
                     "first_down_good_plus":first is not None and
                         first["note_id"]==f"probe-{i}" and event["hit_value"]>=200,
                     "judgement":event["judgement"],"hit_value":event["hit_value"]})
    return rows


def main() -> None:
    spec=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert spec["stage"]=="A9" and spec["seed"]==2002 and spec["one_based_outcome"]==373
    source=json.loads((A82_OUT/"result.json").read_text(encoding="utf-8"))
    a5=json.loads((A5/"result.json").read_text(encoding="utf-8"))
    edges=a5["source_pathway_structure"]["edge_metadata"]
    mask=[i for i,e in enumerate(edges)
          if e["preferred_time_to_contact_us"] in EARLY]
    assert len(mask)==192
    no_data=(A82_OUT/"no_update_checkpoint.pkl").read_bytes()
    no=TinyLaneSession.from_trusted_checkpoint_bytes(no_data)
    clone=TinyLaneSession.from_trusted_checkpoint_bytes(no_data)
    before=weights(no)
    lo=clone.plasticity.parameters.w_min_mv
    for i in mask:
        clone.plasticity._weights[clone.layout.plastic_slots[i]]=lo
    assert_same_state_except_weights(no,clone)
    after=weights(clone)
    assert all(after[i]==before[i] for i in range(480) if i not in mask)
    reference=source["branches"]["no_update"]["probe"]
    times=tuple(reference["checkpoint_time_us"]+x
                for x in reference["relative_note_offsets_us"])
    gains=tuple(reference["cue_gains"])
    OUT.mkdir(parents=True,exist_ok=True)
    atomic_json(OUT/"status.json",{"status":"running","protocol_sha256":sha(PROTOCOL)})
    data=clone.checkpoint_bytes()
    (OUT/"witness_checkpoint.pkl").write_bytes(data)
    probe,trace=probe_with_readout_trace(data,times,gains)
    actions=note_actions(probe)
    count=sum(r["first_down_good_plus"] for r in actions)
    classification="NARROW_EXISTENCE_WITNESS" if count>0 else "WITNESS_FAILED"
    result={
        "status":"complete","study_id":spec["study_id"],
        "protocol_sha256":sha(PROTOCOL),"a82_result_sha256":sha(A82_OUT/"result.json"),
        "a5_result_sha256":sha(A5/"result.json"),
        "source_sha256":sha(ROOT/"scripts/a9_timing_controllability_witness.py"),
        "selected_indices":mask,
        "selected_edge_slots":[clone.layout.plastic_slots[i] for i in mask],
        "weights_before_mv":before,"weights_after_mv":after,
        "weight_delta_mv":[a-b for a,b in zip(after,before)],
        "weight_delta_norm":norm([a-b for a,b in zip(after,before)]),
        "checkpoint_sha256":sha(OUT/"witness_checkpoint.pkl"),
        "probe":probe,"readout_trace":trace,"first_note":first_note(probe,trace),
        "timing":timing_summary(probe),"note_actions":actions,
        "first_down_good_plus_count":count,
        "silent_note_count":sum(r["first_down"] is None for r in actions),
        "comparison_no_update_first_down_good_plus_count":sum(
            r["first_down_good_plus"] for r in note_actions(reference)),
        "classification":classification,
        "completed_utc":datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUT/"result.json",result)
    atomic_json(OUT/"status.json",{"status":"complete",
                                    "protocol_sha256":sha(PROTOCOL),
                                    "result_sha256":sha(OUT/"result.json")})
    print(json.dumps({"classification":classification,
                      "first_down_good_plus":count,
                      "silent_notes":result["silent_note_count"],
                      "total_good_plus":probe["metrics"]["good_or_better_count"],
                      "utility":probe["metrics"]["mean_utility"],
                      "first_crossing":result["first_note"]["first_on_threshold_rise_us"],
                      "changed_edges":sum(a!=b for a,b in zip(after,before))}),flush=True)


if __name__=="__main__":
    main()
