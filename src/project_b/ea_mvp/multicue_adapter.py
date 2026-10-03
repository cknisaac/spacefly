"""Fixed current-frame routing for task-free Freedom Dive cue admission.

All behavior here is an ENGINEERING ASSUMPTION. This adapter stores no chart
schedule or note IDs and does not change fly weights.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Iterable
from project_b.ea_mvp.screen_ttc import ScreenTimeToContactEncoder


@dataclass(frozen=True, slots=True)
class VisualHead:
    lane: int
    position: float
    kind: str  # "tap" or "hold", visible shape classification from this frame

    def __post_init__(self):
        if type(self.lane) is not int or self.lane not in range(4):
            raise ValueError('lane must be in [0, 3]')
        if type(self.position) not in (float, int) or not math.isfinite(self.position) or not 0 <= self.position <= 1:
            raise ValueError('position must be finite and normalized')
        if self.kind not in ('tap', 'hold'):
            raise ValueError('kind must be tap or hold')


@dataclass(frozen=True, slots=True)
class VisualTail:
    lane: int
    position: float

    def __post_init__(self):
        if type(self.lane) is not int or self.lane not in range(4):
            raise ValueError('lane must be in [0, 3]')
        if type(self.position) not in (float, int) or not math.isfinite(self.position):
            raise ValueError('tail position must be finite')


@dataclass(frozen=True, slots=True)
class VisualFrame:
    heads: tuple[VisualHead, ...] = ()
    tails: tuple[VisualTail, ...] = ()

    def __post_init__(self):
        if len(self.heads) > 14:
            raise ValueError('frame exceeds the FD-1 maximum of 14 visible heads')
        if len(self.tails) > 6:
            raise ValueError('frame exceeds the FD-1 maximum of six visible hold-tail render fragments')


@dataclass(frozen=True, slots=True)
class SelectedCue:
    position: float
    lanes: tuple[int, ...]
    kinds_by_lane: tuple[tuple[int, str], ...]


def select_nearest_head(frame: VisualFrame) -> SelectedCue | None:
    """Choose the largest rendered y; exact visible-position ties fan out."""
    if not frame.heads:
        return None
    p = max(float(head.position) for head in frame.heads)
    tied = tuple(head for head in frame.heads if float(head.position) == p)
    if len({head.lane for head in tied}) != len(tied):
        raise ValueError('same-lane heads at the same rendered position are ambiguous')
    ordered = tuple(sorted(tied, key=lambda head: head.lane))
    return SelectedCue(p, tuple(head.lane for head in ordered),
                       tuple((head.lane, head.kind) for head in ordered))


def frame_from_renderer(rows: Iterable[dict]) -> VisualFrame:
    """Crop playfield overdraw and invert FD-1's receptor-to-top coordinate.

    ENGINEERING ASSUMPTION: only heads in the visible playfield [0, 1] are
    current sensory inputs. FD-1 stores raw position 0 at the strike line and
    1 at the top; progress for the fly input is 1 - raw_position.
    Tails at/past the strike line are clamped to 0 so release cannot be skipped
    by a one-pixel/frame crossing.
    """
    source = tuple(rows)
    hold_lanes = {row.get('lane') for row in source if row.get('part') == 'tail'}
    heads: list[VisualHead] = []
    tails: list[VisualTail] = []
    for row in source:
        lane, raw = row.get('lane'), row.get('normalized_position')
        part = row.get('part')
        if type(lane) is not int or type(raw) not in (int, float) or not math.isfinite(raw):
            raise ValueError('renderer tuple must contain finite lane and position values')
        if part == 'head':
            if 0.0 <= raw <= 1.0:
                # FD-1 has no object ID or shape label. A co-visible tail in
                # the same lane is the only current-frame evidence for a hold.
                kind = row.get('kind', 'hold' if lane in hold_lanes else 'tap')
                heads.append(VisualHead(lane, 1.0-float(raw), kind))
        elif part == 'tail':
            if raw <= 1.0:
                tails.append(VisualTail(lane,max(0.0,float(raw))))
        else:
            raise ValueError('renderer tuple part must be head or tail')
    # Several future hold tails can be visible in one lane. With no object ID,
    # retain the closest current tail (smallest raw position) for that lane.
    nearest_tails: dict[int, VisualTail] = {}
    for tail in tails:
        if tail.lane not in nearest_tails or tail.position < nearest_tails[tail.lane].position:
            nearest_tails[tail.lane] = tail
    return VisualFrame(tuple(heads),tuple(nearest_tails[lane] for lane in sorted(nearest_tails)))


class HoldKeyState:
    """Fixed key-state bookkeeping for at most two currently active holds."""
    def __init__(self, *, max_active_holds: int = 2):
        if type(max_active_holds) is not int or max_active_holds != 2:
            raise ValueError('FD-1 admitted capacity is fixed at two active holds')
        self.max_active_holds = max_active_holds
        self.held_lanes: set[int] = set()

    def key_down(self, lane: int, *, hold: bool) -> None:
        if type(lane) is not int or lane not in range(4):
            raise ValueError('lane must be in [0, 3]')
        if hold:
            self.held_lanes.add(lane)
            if len(self.held_lanes) > self.max_active_holds:
                self.held_lanes.remove(lane)
                raise ValueError('active-hold capacity exceeded')

    def observe_tails(self, tails: Iterable[VisualTail]) -> tuple[int, ...]:
        by_lane: dict[int, float] = {}
        for tail in tails:
            by_lane[tail.lane] = min(by_lane.get(tail.lane, math.inf),tail.position)
        released = tuple(sorted(lane for lane in self.held_lanes
                                if lane in by_lane and by_lane[lane] <= 0.0))
        self.held_lanes.difference_update(released)
        return released

    def tap_release(self, lane: int) -> bool:
        """Suppress the fixed tap UP if this lane is still held by a hold."""
        return lane not in self.held_lanes


@dataclass(frozen=True, slots=True)
class LaneTTCState:
    lane: int
    position: float | None
    countdown: float | None
    remaining_us: float | None
    cue_active: bool


class LaneTTCBank:
    """Fixed per-lane visual motion histories for current visible heads only."""
    def __init__(self, *, dt_us: int = 1000, velocity_window_us: int = 50_000,
                 target_lead_us: int = 500_000, pixel_step: float = 1/560):
        self.encoders=[ScreenTimeToContactEncoder(dt_us=dt_us,velocity_window_us=velocity_window_us,
                                                   target_lead_us=target_lead_us) for _ in range(4)]
        self.last_positions:list[float|None]=[None]*4
        self.last_countdowns:list[float|None]=[None]*4
        self.latched=[False]*4
        self.pixel_step=pixel_step

    def reset_lane(self,lane:int)->None:
        self.encoders[lane].reset(); self.last_positions[lane]=None
        self.last_countdowns[lane]=None; self.latched[lane]=False

    def observe(self,time_us:int,frame:VisualFrame)->tuple[LaneTTCState,...]:
        out=[]
        for lane in range(4):
            heads=[head for head in frame.heads if head.lane==lane]
            if not heads:
                self.reset_lane(lane)
                out.append(LaneTTCState(lane,None,None,None,False)); continue
            # ENGINEERING ASSUMPTION: nearest current head in a lane is the one
            # with maximum transformed progress. No IDs or future schedule.
            p=max(float(head.position) for head in heads)
            prev=self.last_positions[lane]
            if prev is not None and p<prev-self.pixel_step:
                self.reset_lane(lane)
            sample=self.encoders[lane].observe(time_us,p)
            q=self.last_countdowns[lane]
            if sample is not None:
                q=sample.countdown if q is None else min(q,sample.countdown)
                self.last_countdowns[lane]=q
                if sample.cue_active:self.latched[lane]=True
            self.last_positions[lane]=p
            out.append(LaneTTCState(lane,p,q,None if sample is None else sample.remaining_us,
                                    self.latched[lane]))
        return tuple(out)
