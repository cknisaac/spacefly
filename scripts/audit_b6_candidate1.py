"""Read saved evidence and local timing events; never import or run the simulator."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/figures/b6_candidate1_decision'
OUT.mkdir(parents=True, exist_ok=True)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

checks = []
def check(path, expected):
    actual = sha(path.read_bytes())
    checks.append(dict(path=path.relative_to(ROOT).as_posix(), expected=expected,
                       actual=actual, matches=actual == expected))

b3 = ROOT / 'docs/figures/b3_controllability_v2'
for arm in read(b3 / 'arm_results.json'):
    stem = f"seed_{arm['seed']}_{arm['level']}_{arm['arm']}"
    check(b3 / (stem + '_ledger.json'), arm['ledger_sha256'])
    check(b3 / (stem + '_first_action.json'), arm['first_action_audit_sha256'])
b31 = ROOT / 'docs/figures/b3_1_mbon05_input_transfer'
receipt = read(b31 / 'receipt.json')
for arm in receipt['arms']:
    for suffix, key in [('ledger', 'ledger_sha256'), ('first_action', 'first_action_audit_sha256'),
                        ('selective_trace', 'selective_trace_sha256'),
                        ('mbon05_source_arrivals', 'source_arrivals_sha256')]:
        check(b31 / f"{arm['arm']}_{suffix}.json", arm[key])
check(ROOT / 'configs/b3_controllability_protocol.json', read(b3 / 'receipt.json')['protocol_sha256'])
check(ROOT / 'configs/b2_1_candidate1_resolved.json', read(b3 / 'receipt.json')['circuit_resolved_sha256'])
check(ROOT / 'configs/b3_1_mbon05_input_transfer.json', receipt['protocol_sha256'])

files = set(ROOT.glob('docs/B[123]*.md')) | set(ROOT.glob('docs/A[12345]*.md'))
for prefix in ['b1_', 'b2_', 'b2_1_', 'b3_', 'a1_', 'a2_', 'a3_', 'a4_', 'a5_']:
    for folder in (ROOT / 'docs/figures').glob(prefix + '*'):
        files.update(folder.rglob('*.json'))
files.update(ROOT.glob('configs/b[23]*.json'))
manifest = [dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size,
                 sha256=sha(p.read_bytes())) for p in sorted(files) if p.is_file()]
save('evidence_audit.json', dict(stage='MVP-B6', checks=checks,
     all_checks_pass=all(c['matches'] for c in checks), preserved_artifacts=manifest,
     source_identity=receipt['source_identity'], scope='Saved bytes only; no neural replay; full upstream source data not rehashed.'))
assert all(c['matches'] for c in checks), 'Saved evidence hash mismatch'

cutoff = datetime.now(timezone.utc)
start = datetime.fromisoformat('2026-10-01T01:30:40.196+00:00')
sources, rows = [], []
for branch, thread in [('A', '01a0f50e-3085-72f1-97e2-a6e0881f0622'),
                       ('B', '01a0f50e-5cb5-7c23-aea0-6f90da065f26')]:
    path, = (Path.home() / '.codex/sessions/2026/10/01').glob('*' + thread + '.jsonl')
    data = path.read_bytes()
    sources.append(dict(branch=branch, path=str(path), snapshot_bytes=len(data), snapshot_sha256=sha(data)))
    starts, ends = {}, {}
    for line in data.splitlines():
        event = json.loads(line)
        p = event.get('payload', {})
        if event.get('type') != 'event_msg':
            continue
        if p.get('type') == 'task_started':
            starts[p['turn_id']] = (event, sha(line))
        if p.get('type') in ['task_complete', 'turn_aborted']:
            ends[p['turn_id']] = (event, sha(line))
    for turn, (event, line_hash) in starts.items():
        began = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
        ending = ends.get(turn)
        ended = datetime.fromisoformat(ending[0]['timestamp'].replace('Z', '+00:00')) if ending else cutoff
        if ended < start:
            continue
        duration = ending[0]['payload']['duration_ms'] if ending else int((cutoff - began).total_seconds() * 1000)
        rows.append(dict(branch=branch, turn_id=turn, start=began.isoformat(), end_or_cutoff=ended.isoformat(),
                         charged_ms=duration, status=ending[0]['payload']['type'] if ending else 'active_at_cutoff',
                         start_event_sha256=line_hash, end_event_sha256=ending[1] if ending else None))
total = sum(r['charged_ms'] for r in rows)
reserve = 600000
ledger = dict(stage='MVP-B6', cutoff_utc=cutoff.isoformat(), candidates_started=1, maximum_candidates=3,
    candidate_cap_ms=28800000, overall_cap_ms=86400000, sources=sources, turns=rows,
    accounting_policy='All A and B root active turns overlapping or after B1 start charged fully to C1; concurrent turns summed; aborted and status turns included; idle gaps excluded. Nested approval work already inside root duration. Local agent time only, not human time or off-platform work.',
    previous_subtotal_ms=2235000, previous_subtotal_treatment='Superseded by full turn accounting, not added twice; original ledgers preserved.',
    recorded_active_ms=total, closeout_reserve_ms=reserve, committed_upper_bound_ms=total+reserve,
    candidate_remaining_after_reserve_ms=28800000-total-reserve,
    overall_remaining_after_reserve_ms=86400000-total-reserve,
    branch_totals_ms={b:sum(r['charged_ms'] for r in rows if r['branch']==b) for b in ['A','B']})
save('budget_reconciliation.json', ledger)
print(json.dumps({k:v for k,v in ledger.items() if k not in ['turns','sources','accounting_policy']}, indent=2))
print(f'Verified {len(checks)} recorded hashes; pinned {len(manifest)} artifacts.')
