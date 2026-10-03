"""Replay the frozen FD-4 fly trace in the existing Pygame Mania renderer.

Run with ``python -m project_b.ea_mvp.replay_companion``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any

from project_b.osu.beatmap import extract_osz, is_native_4k
from project_b.osu.config import OsuConfig
from project_b.osu.mania_game import ManiaGame
from project_b.osu.playable import PlayableMania
from project_b.osu.types import KeyAction, KeyActionKind

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAP = Path(r"C:\Users\imdef\AppData\Roaming\osu\exports\xi - FREEDOM DiVE (razlteh).osz")
DEFAULT_TRACE = ROOT / "runs/ea_mvp/fd4_chart_playback_v4.json"
EXPECTED_MAP_SHA256 = "ced99e231e7eee354feef04bbcde6889178814cb688325bccdeeeacb00dcbff9"


def load_actions(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Preserve the already timestamp-ordered FD-4 transition trace."""
    return [
        {"time_us": int(row["time_us"]), "lane": int(row["lane"]), "kind": row["kind"]}
        for row in trace["runs"][0]["actions"]
    ]


def rebuild_game(beatmap, actions: list[dict[str, Any]], at_us: int):
    """Rebuild state from the trace so seeking never invents input events."""
    game = ManiaGame(beatmap.notes, OsuConfig(od=beatmap.od, ruleset="lazer"))
    index = 0
    while index < len(actions) and actions[index]["time_us"] <= at_us:
        row = actions[index]
        game.apply_action(KeyAction(row["time_us"], row["lane"], KeyActionKind(row["kind"])))
        index += 1
    game.advance_to(max(at_us, game.now_us))
    return game, index


class SavedFlyReplay(PlayableMania):
    """Saved action trace over the unchanged recreation renderer and game rules."""

    def __init__(self, map_path: Path, trace_path: Path):
        import pygame

        super().__init__([map_path])
        self._trace = json.loads(trace_path.read_text(encoding="utf-8"))
        if (self._trace.get("status") != "PASS"
                or self._trace.get("no_training") is not True
                or self._trace.get("no_game_feedback") is not True
                or self._trace["runs"][0].get("weights_unchanged") is not True):
            raise ValueError("the companion requires a passing frozen-weight FD-4 trace")
        self._actions = load_actions(self._trace)
        self._action_index = 0
        self._replay_time_us = 0
        self._audio_started = False
        self._last_action_label = "waiting for first saved key event"
        self._start()
        assert self.beatmap is not None
        if (self.beatmap.sha256 != EXPECTED_MAP_SHA256
                or self.beatmap.sha256 != self._trace["chart"]["sha256"]):
            raise ValueError("selected chart does not match the frozen FD-4 trace")
        pygame.display.set_caption("Spacefly • Freedom Dive saved fly replay")
        self.font = pygame.font.SysFont("Segoe UI", 22)
        self._rebuild(0)

    def _time_us(self) -> int:
        if self.scene == "pause":
            return self._replay_time_us
        return max(self._replay_time_us, (time.perf_counter_ns() - self.anchor_ns) // 1000)

    def _rebuild(self, target_us: int) -> None:
        assert self.beatmap is not None
        target = max(0, min(int(target_us), self.beatmap.end_time_us + 2_000_000))
        self.game, self._action_index = rebuild_game(self.beatmap, self._actions, target)
        self._replay_time_us = target
        self.current_us = target
        self.anchor_ns = time.perf_counter_ns() - target * 1000
        self.last_result = self.game.results[-1].result if self.game.results else ""
        self._last_action_label = "trace state rebuilt at seek point"
        if self.scene == "results" and target < self.beatmap.end_time_us + 1_000_000:
            self.scene = "play"
        if self._audio_started:
            try:
                self.pg.mixer.music.play(start=target / 1_000_000)
                if self.scene == "pause":
                    self.pg.mixer.music.pause()
            except self.pg.error:
                pass

    def _toggle_pause(self) -> None:
        if self.scene == "play":
            self._replay_time_us = self._time_us()
            self.pg.mixer.music.pause()
            self.scene = "pause"
        elif self.scene == "pause":
            self.anchor_ns = time.perf_counter_ns() - self._replay_time_us * 1000
            self.pg.mixer.music.unpause()
            self.scene = "play"

    def _handle_event(self, event) -> bool:
        if event.type in (self.pg.KEYDOWN, self.pg.KEYUP) and event.key in self._keymap:
            return True
        if event.type == self.pg.KEYDOWN and event.key in (self.pg.K_LEFT, self.pg.K_RIGHT):
            delta = -5_000_000 if event.key == self.pg.K_LEFT else 5_000_000
            self._rebuild(self._time_us() + delta)
            return True
        if event.type == self.pg.KEYDOWN and event.key == self.pg.K_r:
            self.pg.mixer.music.stop()
            self._audio_started = False
            self.scene = "play"
            self._rebuild(0)
            return True
        if event.type == self.pg.KEYDOWN and event.key == self.pg.K_ESCAPE:
            self.pg.mixer.music.stop()
            return False
        return super()._handle_event(event)

    def _tick(self) -> None:
        if self.scene not in ("play", "pause") or self.game is None or self.beatmap is None:
            return
        at_us = self._time_us()
        if self.scene == "play" and not self._audio_started:
            try:
                self.pg.mixer.music.play()
            except self.pg.error:
                pass
            self._audio_started = True
        if self.scene == "play":
            while (self._action_index < len(self._actions)
                   and self._actions[self._action_index]["time_us"] <= at_us):
                row = self._actions[self._action_index]
                self.game.apply_action(KeyAction(
                    row["time_us"], row["lane"], KeyActionKind(row["kind"])))
                key = ("D", "F", "J", "K")[row["lane"]]
                self._last_action_label = (
                    f"{row['kind'].upper()} {key} at {row['time_us'] / 1_000_000:.3f}s")
                self._action_index += 1
            self.current_us = max(at_us, self.game.now_us)
            self.game.advance_to(self.current_us)
            self._replay_time_us = at_us
        if (self.game.resolved_objects == len(self.beatmap.notes)
                and at_us >= self.beatmap.end_time_us + 1_000_000):
            self.game.finish()
            self.pg.mixer.music.stop()
            self.scene = "results"

    def _draw_playfield(self, width: int, height: int) -> None:
        super()._draw_playfield(width, height)
        self.screen.blit(self.font.render(
            "SAVED FLY REPLAY  •  frozen weights  •  not live neural activity",
            True, (255, 210, 111)), (30, height - 64))
        action = f"Actions {self._action_index}/{len(self._actions)}   {self._last_action_label}"
        self.screen.blit(self.small.render(action, True, (185, 210, 230)), (30, 43))
        self.screen.blit(self.small.render(
            "← / → seek 5s    P pause/resume    R restart    Esc close",
            True, (150, 165, 190)), (30, height - 33))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    args = parser.parse_args()
    maps = (tuple(p for p in extract_osz(args.map)
                  if is_native_4k(p) and "4K Normal" in p.name)
            if args.map.suffix.lower() == ".osz" else (args.map,))
    if len(maps) != 1:
        parser.error(f"expected one Freedom Dive 4K Normal map, found {len(maps)}")
    SavedFlyReplay(maps[0], args.trace).run()


if __name__ == "__main__":
    main()
