"""Independent selected-weight geometry, state and frozen-probe audit for A8.2."""

from __future__ import annotations

import json
import math
from pathlib import Path

from project_b.experiments import TinyLaneSession
from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.a8_2_first_action_local_direction import A5, BRANCHES, OUT, PROTOCOL, ROOT, sha
from scripts.audit_cue_300ms_necessity_diagnostic import audit_readout
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == status["status"] == "complete"
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert result["protocol_sha256"] == status["protocol_sha256"] == sha(PROTOCOL)
    assert result["a5_result_sha256"] == sha(A5 / "result.json")
    assert all(sha(ROOT / name) == h for name,h in result["source_sha256"].items())
    assert tuple(spec["branches"]) == BRANCHES
    first = TinyLaneSession.from_trusted_checkpoint_bytes(
        (OUT / "first_down_checkpoint.pkl").read_bytes())
    assert sha(OUT / "first_down_checkpoint.pkl") == result["first_down_checkpoint_sha256"]
    assert first.simulator.current_time_us == spec["first_down_time_us"]
    assert first.resolved_count == 372
    assert first.game.result().actions[-1].action.time_us == spec["first_down_time_us"]
    assert first.game.result().actions[-1].disposition.value == "null_press"
    slots = first.layout.plastic_slots
    assert len(slots) == 480
    e = [first.plasticity.eligibility_at(slot,spec["first_down_time_us"]) for slot in slots]
    before = weights(first)
    assert result["first_down_eligibility"] == e
    assert result["first_down_weights_mv"] == before
    assert result["eta"] == first.plasticity.parameters.eta
    assert result["first_action_diagnostic_rpe"] == spec["diagnostic_first_action_rpe"]
    raw = [result["eta"]*value*spec["diagnostic_first_action_rpe"] for value in e]
    assert result["candidate_raw_delta_mv"] == raw
    no = TinyLaneSession.from_trusted_checkpoint_bytes(
        (OUT / "no_update_checkpoint.pkl").read_bytes())
    assert weights(no) == before
    assert result["saved_pre_state_fieldwise_equal"] is True
    assert result["exact_training_events_replayed"] == 373
    lo,hi = no.plasticity.parameters.w_min_mv,no.plasticity.parameters.w_max_mv
    total_notes=total_downs=total_rises=0
    for name in BRANCHES:
        path=OUT/f"{name}_checkpoint.pkl"
        data=path.read_bytes()
        branch=TinyLaneSession.from_trusted_checkpoint_bytes(data)
        item=result["branches"][name]
        assert sha(path) == item["checkpoint_sha256"]
        assert weights(branch) == item["weights_after_mv"]
        assert_same_state_except_weights(no,branch)
        probe=item["probe"]
        trace=item["readout_trace"]
        if name=="no_update":
            assert probe==a5["branches"]["no_update"]["probe"]
        elif name=="historical_real_full":
            assert probe==a5["branches"]["real_full"]["probe"]
        else:
            fraction=spec["small_fraction_of_raw_candidate"] if name.endswith("5_percent") else 1.0
            geom=result["candidate_geometry"][name]
            assert geom["fraction"]==fraction
            proposed=[w+fraction*d for w,d in zip(before,raw)]
            after=[min(hi,max(lo,w)) for w in proposed]
            applied=[a-w for a,w in zip(after,before)]
            assert geom["raw_delta_mv"]==[fraction*d for d in raw]
            assert geom["weights_after_mv"]==after==weights(branch)
            assert geom["applied_delta_mv"]==applied
            assert geom["proposed_below_min_edges"]==sum(w<lo for w in proposed)
            assert geom["proposed_above_max_edges"]==sum(w>hi for w in proposed)
            assert geom["lower_bound_edges_after"]==sum(w==lo for w in after)
            assert geom["upper_bound_edges_after"]==sum(w==hi for w in after)
            for key,vector in (("raw_norm",geom["raw_delta_mv"]),
                               ("applied_norm",applied)):
                norm=geom[key]
                assert math.isclose(norm["l1_mv"],sum(abs(v) for v in vector),abs_tol=1e-9)
                assert math.isclose(norm["l2_mv"],math.sqrt(sum(v*v for v in vector)),abs_tol=1e-9)
                assert math.isclose(norm["max_abs_mv"],max(abs(v) for v in vector),abs_tol=1e-9)
        readout=audit_readout(trace,probe,data)
        total_rises+=readout["on_rise_count"]
        assert probe["exploration"] is False and probe["exploration_pulses_us"]==[]
        assert len(probe["events"])==32 and all(e["weight_changes"]==0 for e in probe["events"])
        assert probe["frozen_weight_sum_mv"]==sum(weights(branch))
        assert probe["frozen_weight_upper_bound_edges"]==sum(w==hi for w in weights(branch))
        note_times=[probe["checkpoint_time_us"]+x for x in probe["relative_note_offsets_us"]]
        game=GameEnvironment(tuple(TapNote(f"probe-{i}",0,t) for i,t in enumerate(note_times)))
        game.current_time_us=probe["checkpoint_time_us"]
        game._key_down[0]=trace["initial"]["key_down"]
        reconstructed_downs=[]
        for d in trace["readout_decisions"]:
            rec=game.apply_action(KeyAction(d["time_us"],0,KeyActionKind(d["kind"])))
            if d["kind"]=="down":
                reconstructed_downs.append({
                    "time_us":d["time_us"],
                    "relative_time_us":d["time_us"]-probe["checkpoint_time_us"],
                    "disposition":rec.disposition.value,
                    "note_id":rec.note_id})
        assert reconstructed_downs==probe["down_actions"]
        judgements=game.finish().judgements
        assert len(judgements)==32
        for j,event in zip(judgements,probe["events"]):
            assert j.judgement.name==event["judgement"]
            assert j.hit_error_us==event["hit_error_us"]
            assert j.note_time_us==event["note_time_us"]
        first_rise=next((x["time_us"] for x in trace["threshold_crossings"]
                         if x["threshold"]=="on" and x["direction"]=="rise"),None)
        assert item["first_note"]["first_on_threshold_rise_us"]==first_rise
        assert item["first_note"]["first_down_us"]==(
            reconstructed_downs[0]["time_us"] if reconstructed_downs else None)
        total_notes+=len(judgements)
        total_downs+=len(reconstructed_downs)
    assert result["classification"]=="INCONCLUSIVE_NO_CROSSING_MOVEMENT"
    receipt={"status":"passed","stage":"A8.2","branches":len(BRANCHES),
             "frozen_notes_rejudged":total_notes,"down_actions_replayed":total_downs,
             "motor_on_rises_recomputed":total_rises,
             "protocol_sha256":sha(PROTOCOL),"result_sha256":sha(OUT/"result.json")}
    (OUT/"audit.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt))


if __name__=="__main__":
    main()
