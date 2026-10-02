"""One structural far-cue component of the A8.2 candidate at fixed state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.a8_2_first_action_local_direction import OUT as A82_OUT, norm
from scripts.cue_300ms_necessity_diagnostic import probe_with_readout_trace
from scripts.cue_300ms_saturation_contrast_diagnostic import first_note
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.long_continuation import atomic_json, sha
from scripts.successive_update_interference_diagnostic import timing_summary


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a8_3_far_cue_component.json"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
OUT = ROOT / "docs/figures/a8_3_far_cue_component"


def main() -> None:
    spec=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert spec["seed"]==2002 and spec["one_based_outcome"]==373
    source=json.loads((A82_OUT/"result.json").read_text(encoding="utf-8"))
    a5=json.loads((A5/"result.json").read_text(encoding="utf-8"))
    edges=a5["source_pathway_structure"]["edge_metadata"]
    raw=source["candidate_raw_delta_mv"]
    assert len(edges)==len(raw)==480
    mask=[i for i,edge in enumerate(edges)
          if edge["preferred_time_to_contact_us"] in (400_000,500_000)]
    assert len(mask)==96
    before=source["first_down_weights_mv"]
    no_data=(A82_OUT/"no_update_checkpoint.pkl").read_bytes()
    no=TinyLaneSession.from_trusted_checkpoint_bytes(no_data)
    assert weights(no)==before
    clone=TinyLaneSession.from_trusted_checkpoint_bytes(no_data)
    lo,hi=clone.plasticity.parameters.w_min_mv,clone.plasticity.parameters.w_max_mv
    proposed=[w+(raw[i] if i in mask else 0.0) for i,w in enumerate(before)]
    after=[min(hi,max(lo,w)) for w in proposed]
    for slot,value in zip(clone.layout.plastic_slots,after):
        clone.plasticity._weights[slot]=value
    assert_same_state_except_weights(no,clone)
    assert all(after[i]==before[i] for i in range(480) if i not in mask)
    applied=[a-w for a,w in zip(after,before)]
    reference=source["branches"]["no_update"]["probe"]
    note_times=tuple(reference["checkpoint_time_us"]+x
                     for x in reference["relative_note_offsets_us"])
    gains=tuple(reference["cue_gains"])
    OUT.mkdir(parents=True,exist_ok=True)
    atomic_json(OUT/"status.json",{"status":"running","protocol_sha256":sha(PROTOCOL)})
    checkpoint=clone.checkpoint_bytes()
    (OUT/"far_cue_only_checkpoint.pkl").write_bytes(checkpoint)
    probe,trace=probe_with_readout_trace(checkpoint,note_times,gains)
    first=first_note(probe,trace)
    no_t=source["branches"]["no_update"]["first_note"]["first_on_threshold_rise_us"]
    far_t=first["first_on_threshold_rise_us"]
    if far_t is None or first["first_down_us"] is None or far_t==no_t:
        classification="INCONCLUSIVE_NO_CROSSING_MOVEMENT_OR_SILENCE"
    elif far_t>no_t:
        classification="USEFUL_FAR_DIRECTION_AT_THIS_STATE"
    else:
        classification="OPPOSING_FAR_DIRECTION_AT_THIS_STATE"
    result={
        "status":"complete","study_id":spec["study_id"],
        "protocol_sha256":sha(PROTOCOL),
        "a82_result_sha256":sha(A82_OUT/"result.json"),
        "a5_result_sha256":sha(A5/"result.json"),
        "source_sha256":sha(ROOT/"scripts/a8_3_far_cue_component.py"),
        "selected_indices":mask,
        "selected_edge_slots":[clone.layout.plastic_slots[i] for i in mask],
        "selected_first_action_eligibility_sum":sum(source["first_down_eligibility"][i] for i in mask),
        "total_first_action_eligibility_sum":sum(source["first_down_eligibility"]),
        "raw_delta_mv":[raw[i] if i in mask else 0.0 for i in range(480)],
        "applied_delta_mv":applied,
        "raw_norm":norm([raw[i] if i in mask else 0.0 for i in range(480)]),
        "applied_norm":norm(applied),
        "proposed_below_min_edges":sum(w<lo for w in proposed),
        "proposed_above_max_edges":sum(w>hi for w in proposed),
        "lower_bound_edges_after":sum(w==lo for w in after),
        "upper_bound_edges_after":sum(w==hi for w in after),
        "weights_after_mv":after,
        "checkpoint_sha256":sha(OUT/"far_cue_only_checkpoint.pkl"),
        "probe":probe,"readout_trace":trace,
        "first_note":first,"timing":timing_summary(probe),
        "comparison_first_crossing_us":{
            "a82_no_update":no_t,
            "a82_full_candidate":source["branches"]["first_action_candidate_full"]["first_note"]["first_on_threshold_rise_us"],
            "far_cue_only":far_t,
        },
        "classification":classification,
        "completed_utc":datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUT/"result.json",result)
    atomic_json(OUT/"status.json",{"status":"complete",
                                    "protocol_sha256":sha(PROTOCOL),
                                    "result_sha256":sha(OUT/"result.json")})
    print(json.dumps({"first_crossing_us":result["comparison_first_crossing_us"],
                      "first_down_us":first["first_down_us"],
                      "good_plus":probe["metrics"]["good_or_better_count"],
                      "utility":probe["metrics"]["mean_utility"],
                      "raw_l1":result["raw_norm"]["l1_mv"],
                      "applied_l1":result["applied_norm"]["l1_mv"],
                      "clipped_lower":result["proposed_below_min_edges"],
                      "classification":classification}),flush=True)


if __name__=="__main__":
    main()
