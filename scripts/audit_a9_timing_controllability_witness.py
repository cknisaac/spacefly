"""Independent state, constructed mask, first-action and game audit for A9."""

from __future__ import annotations

import json

from project_b.experiments import TinyLaneSession
from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.a9_timing_controllability_witness import A5, A82_OUT, EARLY, OUT, PROTOCOL, ROOT, sha
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
    assert result["source_sha256"]==sha(ROOT/"scripts/a9_timing_controllability_witness.py")
    no=TinyLaneSession.from_trusted_checkpoint_bytes(
        (A82_OUT/"no_update_checkpoint.pkl").read_bytes())
    path=OUT/"witness_checkpoint.pkl"
    branch=TinyLaneSession.from_trusted_checkpoint_bytes(path.read_bytes())
    assert result["checkpoint_sha256"]==sha(path)
    assert_same_state_except_weights(no,branch)
    edges=a5["source_pathway_structure"]["edge_metadata"]
    mask=[i for i,e in enumerate(edges) if e["preferred_time_to_contact_us"] in EARLY]
    assert len(mask)==192 and result["selected_indices"]==mask
    assert result["selected_edge_slots"]==[branch.layout.plastic_slots[i] for i in mask]
    before=weights(no)
    after=weights(branch)
    lo=branch.plasticity.parameters.w_min_mv
    assert result["weights_before_mv"]==before
    assert result["weights_after_mv"]==after
    assert result["weight_delta_mv"]==[a-b for a,b in zip(after,before)]
    assert all(after[i]==lo for i in mask)
    assert all(after[i]==before[i] for i in range(480) if i not in mask)
    probe=result["probe"]
    trace=result["readout_trace"]
    readout=audit_readout(trace,probe,path.read_bytes())
    assert probe["exploration"] is False and probe["exploration_pulses_us"]==[]
    assert len(probe["events"])==32 and all(e["weight_changes"]==0 for e in probe["events"])
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
    assert all(j.judgement.name==e["judgement"] and j.hit_error_us==e["hit_error_us"]
               for j,e in zip(judged,probe["events"]))
    note_actions=[]
    for i,t in enumerate(times):
        associated=[a for a in downs
                    if t-500_000<=a["time_us"]<=t+game.windows.expiry_offset_us]
        first=associated[0] if associated else None
        event=probe["events"][i]
        note_actions.append({
            "note_index":i,"note_time_us":t,"first_down":first,
            "first_down_offset_us":first["time_us"]-t if first else None,
            "down_count":len(associated),
            "first_down_good_plus":first is not None and
                first["note_id"]==f"probe-{i}" and event["hit_value"]>=200,
            "judgement":event["judgement"],"hit_value":event["hit_value"]})
    assert result["note_actions"]==note_actions
    assert result["first_down_good_plus_count"]==sum(r["first_down_good_plus"] for r in note_actions)==0
    assert result["silent_note_count"]==sum(r["first_down"] is None for r in note_actions)==0
    assert probe["metrics"]["good_or_better_count"]==32
    assert probe["metrics"]["null_down_count"]==32
    assert all(r["first_down"]["disposition"]=="null_press" for r in note_actions)
    assert result["classification"]=="WITNESS_FAILED"
    receipt={"status":"passed","stage":"A9","selected_edges":len(mask),
             "frozen_notes_rejudged":len(judged),"down_actions_replayed":len(downs),
             "motor_on_rises_recomputed":readout["on_rise_count"],
             "first_down_good_plus":0,"scored_good_plus":32,
             "protocol_sha256":sha(PROTOCOL),"result_sha256":sha(OUT/"result.json")}
    (OUT/"audit.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt))


if __name__=="__main__":
    main()
