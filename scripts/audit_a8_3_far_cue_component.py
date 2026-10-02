"""Independent mask, weights, readout and game audit for A8.3."""

from __future__ import annotations

import json
import math

from project_b.experiments import TinyLaneSession
from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.a8_3_far_cue_component import A5, A82_OUT, OUT, PROTOCOL, ROOT, sha
from scripts.audit_cue_300ms_necessity_diagnostic import audit_readout
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights


def main() -> None:
    spec=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result=json.loads((OUT/"result.json").read_text(encoding="utf-8"))
    status=json.loads((OUT/"status.json").read_text(encoding="utf-8"))
    source=json.loads((A82_OUT/"result.json").read_text(encoding="utf-8"))
    a5=json.loads((A5/"result.json").read_text(encoding="utf-8"))
    assert result["status"]==status["status"]=="complete"
    assert result["protocol_sha256"]==status["protocol_sha256"]==sha(PROTOCOL)
    assert status["result_sha256"]==sha(OUT/"result.json")
    assert result["a82_result_sha256"]==sha(A82_OUT/"result.json")
    assert result["a5_result_sha256"]==sha(A5/"result.json")
    assert result["source_sha256"]==sha(ROOT/"scripts/a8_3_far_cue_component.py")
    no=TinyLaneSession.from_trusted_checkpoint_bytes(
        (A82_OUT/"no_update_checkpoint.pkl").read_bytes())
    branch_path=OUT/"far_cue_only_checkpoint.pkl"
    branch=TinyLaneSession.from_trusted_checkpoint_bytes(branch_path.read_bytes())
    assert result["checkpoint_sha256"]==sha(branch_path)
    assert_same_state_except_weights(no,branch)
    edges=a5["source_pathway_structure"]["edge_metadata"]
    mask=[i for i,edge in enumerate(edges)
          if edge["preferred_time_to_contact_us"] in (400_000,500_000)]
    assert len(mask)==96 and result["selected_indices"]==mask
    assert result["selected_edge_slots"]==[branch.layout.plastic_slots[i] for i in mask]
    before=source["first_down_weights_mv"]
    raw=source["candidate_raw_delta_mv"]
    lo,hi=branch.plasticity.parameters.w_min_mv,branch.plasticity.parameters.w_max_mv
    proposed=[w+(raw[i] if i in mask else 0.0) for i,w in enumerate(before)]
    after=[min(hi,max(lo,w)) for w in proposed]
    applied=[a-w for a,w in zip(after,before)]
    assert weights(no)==before and weights(branch)==after==result["weights_after_mv"]
    assert result["raw_delta_mv"]==[raw[i] if i in mask else 0.0 for i in range(480)]
    assert result["applied_delta_mv"]==applied
    assert all(after[i]==before[i] for i in range(480) if i not in mask)
    assert result["proposed_below_min_edges"]==sum(w<lo for w in proposed)
    assert result["proposed_above_max_edges"]==sum(w>hi for w in proposed)
    assert result["lower_bound_edges_after"]==sum(w==lo for w in after)
    assert result["upper_bound_edges_after"]==sum(w==hi for w in after)
    for key,vector in (("raw_norm",result["raw_delta_mv"]),("applied_norm",applied)):
        n=result[key]
        assert math.isclose(n["l1_mv"],sum(abs(v) for v in vector),abs_tol=1e-9)
        assert math.isclose(n["l2_mv"],math.sqrt(sum(v*v for v in vector)),abs_tol=1e-9)
    e=source["first_down_eligibility"]
    assert result["selected_first_action_eligibility_sum"]==sum(e[i] for i in mask)
    assert result["total_first_action_eligibility_sum"]==sum(e)
    probe=result["probe"]
    trace=result["readout_trace"]
    readout=audit_readout(trace,probe,branch_path.read_bytes())
    assert probe["exploration"] is False and probe["exploration_pulses_us"]==[]
    assert len(probe["events"])==32 and all(event["weight_changes"]==0 for event in probe["events"])
    times=[probe["checkpoint_time_us"]+x for x in probe["relative_note_offsets_us"]]
    game=GameEnvironment(tuple(TapNote(f"probe-{i}",0,t) for i,t in enumerate(times)))
    game.current_time_us=probe["checkpoint_time_us"]
    game._key_down[0]=trace["initial"]["key_down"]
    downs=[]
    for d in trace["readout_decisions"]:
        record=game.apply_action(KeyAction(d["time_us"],0,KeyActionKind(d["kind"])))
        if d["kind"]=="down":
            downs.append({"time_us":d["time_us"],
                          "relative_time_us":d["time_us"]-probe["checkpoint_time_us"],
                          "disposition":record.disposition.value,"note_id":record.note_id})
    assert downs==probe["down_actions"]
    judged=game.finish().judgements
    assert len(judged)==32
    assert all(j.judgement.name==event["judgement"] and
               j.hit_error_us==event["hit_error_us"]
               for j,event in zip(judged,probe["events"]))
    crossing=next((c["time_us"] for c in trace["threshold_crossings"]
                   if c["threshold"]=="on" and c["direction"]=="rise"),None)
    assert result["first_note"]["first_on_threshold_rise_us"]==crossing
    assert result["comparison_first_crossing_us"]=={
        "a82_no_update":source["branches"]["no_update"]["first_note"]["first_on_threshold_rise_us"],
        "a82_full_candidate":source["branches"]["first_action_candidate_full"]["first_note"]["first_on_threshold_rise_us"],
        "far_cue_only":crossing}
    assert result["classification"]=="INCONCLUSIVE_NO_CROSSING_MOVEMENT_OR_SILENCE"
    receipt={"status":"passed","stage":"A8.3","selected_edges":len(mask),
             "frozen_notes_rejudged":len(judged),"down_actions_replayed":len(downs),
             "motor_on_rises_recomputed":readout["on_rise_count"],
             "protocol_sha256":sha(PROTOCOL),"result_sha256":sha(OUT/"result.json")}
    (OUT/"audit.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt))


if __name__=="__main__":
    main()
