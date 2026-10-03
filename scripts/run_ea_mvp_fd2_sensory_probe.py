"""FD-2 task-free probe for the frozen screen-to-countdown mapping."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path

from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'configs/malecns_continuous_position_learning_v2_5.json'
RECEIPT_ROOT = ROOT / 'runs/ea_mvp/confirmation_fixed_v1'
OUTPUT = ROOT / 'runs/ea_mvp/fd2_sensory_probe_v1.json'
SEEDS = (907, 1009, 1103)
DURATIONS_MS = (1281, 1499, 1786)  # FD-1 min / median / max rendered head lead
DT_US = 1000
ACTION_TOLERANCE_US = 73_500  # unchanged EA13 first-action tolerance


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_arm(seed: int, arm: str) -> dict:
    path = RECEIPT_ROOT / f'seed_{seed}_{arm}.json.gz'
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def play_ramp(config: dict, weights: list[float], duration_ms: int) -> list[dict]:
    policy = ContinuousFourLaneFlyPolicy(config, weights)
    policy.begin(PositionObservation(True, 0, 1.0))
    transitions = []
    total_ms = duration_ms + 150
    for tick_ms in range(1, total_ms + 1):
        if tick_ms <= duration_ms:
            screen_y = tick_ms / duration_ms  # top=0, receptor=1
            countdown = 1.0 - min(1.0, max(0.0, screen_y))
            obs = PositionObservation(True, 0, countdown)
        else:
            obs = PositionObservation(False, 0, None)
        transitions.extend(policy.step(obs))
    policy.finish()
    assert tuple(weights) == policy.weights
    return [{'time_us': row.episode_time_us, 'lane': row.lane, 'kind': row.kind.value}
            for row in transitions]


def passed(actions: list[dict], duration_ms: int) -> tuple[bool, str]:
    downs = [row for row in actions if row['kind'] == KeyActionKind.DOWN.value]
    ups = [row for row in actions if row['kind'] == KeyActionKind.UP.value]
    if len(downs) != 1 or downs[0]['lane'] != 0:
        return False, f'expected one lane-0 DOWN; saw {downs}'
    if abs(downs[0]['time_us'] - duration_ms * 1000) > ACTION_TOLERANCE_US:
        return False, f'DOWN error {downs[0]["time_us"] - duration_ms * 1000} us'
    if len(ups) != 1 or ups[0]['time_us'] != downs[0]['time_us'] + 10_000:
        return False, f'expected one 10-ms UP; saw {ups}'
    return True, 'one lane-0 press inside frozen EA13 timing window; 10-ms release'


def main() -> None:
    config = load_position_config(ROOT, str(CONFIG_PATH.relative_to(ROOT)))
    rows = []
    for seed in SEEDS:
        weights = read_arm(seed, 'learning_on')['final_weights']
        for duration_ms in DURATIONS_MS:
            repeats = []
            for repeat in (1, 2):
                actions = play_ramp(config, weights, duration_ms)
                ok, note = passed(actions, duration_ms)
                repeats.append({'repeat': repeat, 'actions': actions, 'pass': ok, 'note': note})
            rows.append({'arm': 'frozen_learning_on', 'seed': seed,
                         'duration_ms': duration_ms, 'repeats': repeats,
                         'exact_repeat': repeats[0]['actions'] == repeats[1]['actions']})
    # One matched initial-weight control at median geometry duration.
    initial = read_arm(907, 'untrained')['initial_weights']
    actions = play_ramp(config, initial, DURATIONS_MS[1])
    rows.append({'arm': 'untrained', 'seed': 907, 'duration_ms': DURATIONS_MS[1],
                 'repeats': [{'repeat': 1, 'actions': actions,
                              'pass': actions == [],
                              'note': 'silent control' if not actions else 'unexpected action'}]})
    trained_cells = [row for row in rows if row['arm'] == 'frozen_learning_on']
    all_pass = all(rep['pass'] for row in trained_cells for rep in row['repeats'])
    exact = all(row['exact_repeat'] for row in trained_cells)
    untrained = rows[-1]['repeats'][0]['pass']
    result = {
        'protocol': 'EA-MVP-FD2-SENSORY-MAPPING-PROBE-v1',
        'status': 'PASS' if all_pass and exact and untrained else 'FAIL',
        'no_training': True,
        'no_game_or_score': True,
        'frozen_mapping': 'screen_position=clamp((receptor_y-y)/(receptor_y-playfield_top),0,1); EA13_position=1-screen_position',
        'candidate_durations_ms_from_fd1': list(DURATIONS_MS),
        'action_tolerance_us_inherited_from_ea13': ACTION_TOLERANCE_US,
        'source_config_sha256': sha(CONFIG_PATH),
        'weight_receipt_sha256': {str(seed): sha(RECEIPT_ROOT / f'seed_{seed}_learning_on.json.gz') for seed in SEEDS},
        'criteria': 'one DOWN at endpoint ±73.5 ms, one UP exactly 10 ms later, exact repeats, untrained silent, weights unchanged',
        'cases': rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()


