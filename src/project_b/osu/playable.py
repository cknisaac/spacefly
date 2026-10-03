"""Run the playable native 4K osu!mania recreation.

Usage: python -m project_b.osu.playable [map.osu | package.osz | maps_directory]
"""

from __future__ import annotations

import argparse
from array import array
from bisect import bisect_right
from dataclasses import dataclass
from decimal import Decimal
import math
from pathlib import Path
import time
from zipfile import BadZipFile

from .beatmap import ManiaBeatmap, extract_osz, is_native_4k, load_mania_beatmap
from .config import OsuConfig
from .mania_game import ManiaGame
from .types import HoldNote, KeyAction, KeyActionKind, TapNote


KEYS = ("D", "F", "J", "K")
LANE_COLORS = ((98, 168, 255), (248, 132, 182), (248, 132, 182), (98, 168, 255))
BACKGROUND = (12, 16, 29)


@dataclass(frozen=True, slots=True)
class _ScrollSegment:
    time_us: int
    position: float
    multiplier: float


class ScrollMap:
    """Integrate red and inherited timing changes on the same map clock."""

    def __init__(self, beatmap: ManiaBeatmap):
        red_points = [point for point in beatmap.timing_points
                      if point.uninherited and point.beat_length_ms > 0]
        red = [point.beat_length_ms for point in red_points]
        if not red:
            raise ValueError("map has no positive red timing point")
        # osu!lazer's GetMostCommonBeatLength() weights each red point by its
        # duration up to the last playable object, grouping at 0.001 ms.
        durations: dict[Decimal, int] = {}
        last = beatmap.end_time_us
        for index, point in enumerate(red_points):
            key = point.beat_length_ms.quantize(Decimal("0.001"))
            start = 0 if index == 0 else point.time_us
            next_time = (red_points[index + 1].time_us
                         if index + 1 < len(red_points) else last)
            duration = max(0, min(next_time, last) - start) if point.time_us <= last else 0
            durations[key] = durations.get(key, 0) + duration
        common = max(durations, key=durations.get)
        common = min(max(common, min(red)), max(red))
        current_beat = red[0]
        sv = Decimal(1)
        segments: list[_ScrollSegment] = []
        position = 0.0
        previous_time = beatmap.timing_points[0].time_us
        previous_multiplier = float(common / current_beat)
        for point in beatmap.timing_points:
            position += (point.time_us - previous_time) * previous_multiplier
            if point.uninherited:
                if point.beat_length_ms > 0:
                    current_beat = point.beat_length_ms
                    sv = Decimal(1)
            else:
                sv = point.scroll_multiplier
            multiplier = float(sv * common / current_beat)
            segments.append(_ScrollSegment(point.time_us, position, multiplier))
            previous_time = point.time_us
            previous_multiplier = multiplier
        self._segments = tuple(segments)
        self._times = tuple(segment.time_us for segment in segments)

    def position(self, at_us: int) -> float:
        index = max(0, bisect_right(self._times, at_us) - 1)
        segment = self._segments[index]
        return segment.position + (at_us - segment.time_us) * segment.multiplier


class PlayableMania:
    """Pygame presentation around the deterministic game and one audio clock."""

    def __init__(self, paths: list[Path]):
        import pygame

        self.pg = pygame
        pygame.init()
        pygame.key.set_repeat()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except pygame.error as exc:
            raise RuntimeError(f"audio device unavailable: {exc}") from exc
        self.screen = pygame.display.set_mode((1050, 760), pygame.RESIZABLE)
        pygame.display.set_caption("Spacefly 4K mania")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Segoe UI", 27)
        self.small = pygame.font.SysFont("Segoe UI", 19)
        self.large = pygame.font.SysFont("Segoe UI", 56, bold=True)
        self.maps = paths
        self.selected = 0
        self.message = "Press O to choose a .osu map" if not paths else "Enter to play"
        self.scene = "select"
        self.beatmap: ManiaBeatmap | None = None
        self.scroll_map: ScrollMap | None = None
        self.game: ManiaGame | None = None
        self.anchor_ns = 0
        self.paused_us = 0
        self.music_started = False
        self.current_us = 0
        self.last_result = ""
        self.click_sound = self._make_click()
        self.custom_sounds = {}
        self._keymap = {pygame.K_d: 0, pygame.K_f: 1, pygame.K_j: 2, pygame.K_k: 3}

    def _make_click(self):
        samples = array("h")
        for index in range(2205):
            decay = (1 - index / 2205) ** 3
            value = int(8500 * decay * math.sin(2 * math.pi * 880 * index / 44100))
            samples.extend((value, value))
        return self.pg.mixer.Sound(buffer=samples.tobytes())

    def _add_map(self, path: Path) -> None:
        path = path.resolve()
        try:
            candidates = (tuple(p for p in extract_osz(path) if is_native_4k(p))
                          if path.suffix.lower() == ".osz" else (path,))
            if path.suffix.lower() not in (".osu", ".osz"):
                raise ValueError("choose a .osu or .osz file")
            if not candidates:
                raise ValueError("package contains no native 4K maps")
            for candidate in candidates:
                if candidate not in self.maps:
                    self.maps.append(candidate)
            self.selected = self.maps.index(candidates[0])
            self.message = f"Added {len(candidates)} map(s) from {path.name}"
        except (OSError, ValueError, RuntimeError, BadZipFile) as exc:
            self.message = f"Cannot add map: {exc}"

    def _choose_map(self) -> None:
        from tkinter import Tk, filedialog

        root = Tk()
        root.withdraw()
        try:
            chosen = filedialog.askopenfilename(title="Choose a 4K osu!mania map",
                                                filetypes=[("osu! beatmaps", "*.osu *.osz")])
        finally:
            root.destroy()
        if chosen:
            self._add_map(Path(chosen))

    def _start(self) -> None:
        if not self.maps:
            self._choose_map()
            if not self.maps:
                return
        try:
            beatmap = load_mania_beatmap(self.maps[self.selected])
            self.pg.mixer.music.load(str(beatmap.audio_path))
            game = ManiaGame(beatmap.notes, OsuConfig(od=beatmap.od, ruleset="lazer"))
            scroll = ScrollMap(beatmap)
            custom_sounds = {note_id: self.pg.mixer.Sound(str(path))
                             for note_id, path in beatmap.custom_samples}
        except (OSError, ValueError, self.pg.error) as exc:
            self.message = f"Cannot load map: {exc}"
            self.scene = "select"
            return
        self.pg.mixer.music.stop()
        self.beatmap, self.game, self.scroll_map = beatmap, game, scroll
        self.custom_sounds = custom_sounds
        self.anchor_ns = time.perf_counter_ns() + 1_500_000_000
        self.paused_us = 0
        self.music_started = False
        self.current_us = 0
        self.last_result = ""
        self.scene = "play"

    def _time_us(self) -> int:
        if self.scene == "pause":
            return self.paused_us
        return (time.perf_counter_ns() - self.anchor_ns) // 1000

    def _toggle_pause(self) -> None:
        if self.scene == "play":
            self.paused_us = self._time_us()
            if self.music_started:
                self.pg.mixer.music.pause()
            self.scene = "pause"
        elif self.scene == "pause":
            self.anchor_ns = time.perf_counter_ns() - self.paused_us * 1000
            if self.music_started:
                self.pg.mixer.music.unpause()
            self.scene = "play"

    def _finish(self) -> None:
        if self.game is None:
            return
        self.game.finish()
        self.pg.mixer.music.stop()
        self.scene = "results"

    def _handle_event(self, event) -> bool:
        pg = self.pg
        if event.type == pg.QUIT:
            return False
        if event.type == pg.DROPFILE:
            self._add_map(Path(event.file))
            if self.scene != "play":
                self.scene = "select"
        if event.type not in (pg.KEYDOWN, pg.KEYUP):
            return True
        key = event.key
        if event.type == pg.KEYDOWN:
            if key == pg.K_ESCAPE:
                if self.scene in ("play", "pause", "results"):
                    pg.mixer.music.stop()
                    self.scene = "select"
                else:
                    return False
            elif key == pg.K_o and self.scene == "select":
                self._choose_map()
            elif key in (pg.K_UP, pg.K_DOWN) and self.scene == "select" and self.maps:
                self.selected = (self.selected + (1 if key == pg.K_DOWN else -1)) % len(self.maps)
            elif key == pg.K_RETURN and self.scene == "select":
                self._start()
            elif key == pg.K_r and self.scene in ("play", "pause", "results"):
                self._start()
            elif key == pg.K_p and self.scene in ("play", "pause"):
                self._toggle_pause()
        if self.scene == "play" and key in self._keymap and self.game is not None:
            at_us = self._time_us()
            if at_us < 0:
                return True
            kind = KeyActionKind.DOWN if event.type == pg.KEYDOWN else KeyActionKind.UP
            action = KeyAction(max(at_us, self.game.now_us), self._keymap[key], kind)
            result = self.game.apply_action(action)
            if kind is KeyActionKind.DOWN and result.disposition == "hit":
                self.custom_sounds.get(result.note_id, self.click_sound).play()
            if self.game.results:
                self.last_result = self.game.results[-1].result
        return True

    def _tick(self) -> None:
        if self.scene != "play" or self.game is None or self.beatmap is None:
            return
        at_us = self._time_us()
        if at_us >= 0 and not self.music_started:
            self.pg.mixer.music.play()
            self.music_started = True
        if at_us >= 0:
            self.current_us = max(at_us, self.game.now_us)
            self.game.advance_to(self.current_us)
        if (self.game.resolved_objects == len(self.beatmap.notes)
                and at_us >= self.beatmap.end_time_us + 1_000_000):
            self._finish()

    def _text(self, value: str, x: int, y: int, color=(230, 235, 250),
              *, large=False) -> None:
        font = self.large if large else self.font
        self.screen.blit(font.render(value, True, color), (x, y))

    def _draw_select(self, width: int, height: int) -> None:
        self._text("SPACEFLY MANIA", 60, 48, large=True)
        self._text("4K  •  no mods  •  normal rate", 62, 125, (150, 165, 190))
        self._text("O: open map     Enter: play     ↑ ↓: choose     Esc: quit", 62, 180)
        self._text(self.message[:95], 62, height - 55, (255, 194, 113))
        for index, path in enumerate(self.maps[:16]):
            color = (255, 210, 111) if index == self.selected else (190, 205, 230)
            self._text(("▶ " if index == self.selected else "   ") + path.stem[:75],
                       75, 245 + index * 29, color)

    def _draw_playfield(self, width: int, height: int) -> None:
        assert self.beatmap and self.game and self.scroll_map
        pg = self.pg
        top = 75
        line_y = height - 125
        visible_height = line_y - top
        lane_width = min(118, (width - 120) // 4)
        left = (width - lane_width * 4) // 2
        pg.draw.rect(self.screen, (23, 31, 48), (left, top, lane_width * 4, visible_height + 38))
        for lane in range(4):
            rect = (left + lane * lane_width, top, lane_width, visible_height + 38)
            pg.draw.rect(self.screen, (32, 43, 65) if lane % 2 == 0 else (28, 37, 59), rect)
            if self.game.key_down[lane]:
                pg.draw.rect(self.screen, (*LANE_COLORS[lane], 130),
                             (rect[0] + 4, line_y - 35, lane_width - 8, 70))
            pg.draw.line(self.screen, (65, 80, 105), (rect[0], top),
                         (rect[0], line_y + 38), 2)
            self._text(KEYS[lane], rect[0] + lane_width // 2 - 10, line_y + 10)
        pg.draw.line(self.screen, (255, 221, 137), (left, line_y),
                     (left + lane_width * 4, line_y), 4)

        now = self._time_us()
        current_pos = self.scroll_map.position(now)
        time_range_us = 11_485_000 / 8
        resolved = {r.note_id for r in self.game.results
                    if r.component in ("tap", "tail")}
        for note in self.beatmap.notes:
            if note.note_id in resolved:
                continue
            end = note.end_time_us if isinstance(note, HoldNote) else note.time_us
            if end < now - 300_000 or note.time_us > now + 6_000_000:
                continue
            x = left + note.lane * lane_width + 7
            color = LANE_COLORS[note.lane]
            y_head = line_y - int((self.scroll_map.position(note.time_us) - current_pos)
                                  * visible_height / time_range_us)
            if isinstance(note, HoldNote):
                y_tail = line_y - int((self.scroll_map.position(note.end_time_us) - current_pos)
                                      * visible_height / time_range_us)
                state = self.game._holds[note.note_id]
                if state.head and state.head != "MISS" and now >= note.time_us:
                    y_head = line_y
                top_body = max(top, min(y_tail, y_head))
                bottom_body = min(line_y + 30, max(y_tail, y_head))
                if bottom_body > top_body:
                    pg.draw.rect(self.screen, tuple(max(35, c // 2) for c in color),
                                 (x + 9, top_body, lane_width - 32,
                                  bottom_body - top_body))
                if top - 22 <= y_tail <= line_y + 30:
                    pg.draw.rect(self.screen, color,
                                 (x + 3, y_tail - 7, lane_width - 20, 14), border_radius=3)
            if top - 24 <= y_head <= line_y + 35:
                pg.draw.rect(self.screen, color,
                             (x, y_head - 12, lane_width - 14, 24), border_radius=4)
                pg.draw.rect(self.screen, (245, 248, 255),
                             (x, y_head - 12, lane_width - 14, 24), 2, border_radius=4)

        score = self.game.score.snapshot()
        self._text(f"{self.beatmap.title[:39]}  [{self.beatmap.version[:24]}]", 30, 16)
        self._text(f"{score.score:07d}", width - 225, 20)
        self._text(f"{score.accuracy * 100:6.2f}%", width - 195, 57, (162, 224, 250))
        self._text(f"{score.combo}x", left + lane_width * 4 + 25, line_y - 100,
                   (255, 221, 137))
        if self.last_result:
            self._text(self.last_result, left + lane_width * 4 + 25, line_y - 65)
        self.screen.blit(self.small.render("P pause  •  R restart  •  Esc maps", True,
                                           (150, 165, 190)), (30, height - 32))

    def _draw_results(self, width: int, height: int) -> None:
        assert self.game and self.beatmap
        score = self.game.score.snapshot()
        self._text("RESULTS", 60, 55, large=True)
        self._text(f"{self.beatmap.artist} — {self.beatmap.title}", 62, 140)
        self._text(f"Score   {score.score:07d}", 62, 210)
        self._text(f"Accuracy   {score.accuracy * 100:.2f}%", 62, 252)
        self._text(f"Max combo   {score.max_combo}", 62, 294)
        self._text(f"Taps {self.beatmap.tap_count}   Long notes {self.beatmap.hold_count}",
                   62, 336)
        y = 392
        for grade in ("PERFECT", "GREAT", "GOOD", "OK", "MEH", "MISS", "COMBO_BREAK"):
            self._text(f"{grade:<14} {score.result_counts.get(grade, 0)}", 62, y)
            y += 30
        self._text("R: retry     Esc: maps", 62, height - 62, (255, 210, 111))

    def run(self) -> None:
        active = True
        while active:
            for event in self.pg.event.get():
                active = self._handle_event(event) and active
            self._tick()
            width, height = self.screen.get_size()
            self.screen.fill(BACKGROUND)
            if self.scene == "select":
                self._draw_select(width, height)
            elif self.scene == "results":
                self._draw_results(width, height)
            else:
                self._draw_playfield(width, height)
                if self.scene == "pause":
                    shade = self.pg.Surface((width, height), self.pg.SRCALPHA)
                    shade.fill((5, 8, 20, 170))
                    self.screen.blit(shade, (0, 0))
                    self._text("PAUSED", width // 2 - 120, height // 2 - 50,
                               large=True)
                    self._text("P resume    R restart    Esc maps",
                               width // 2 - 170, height // 2 + 25)
            self.pg.display.flip()
            self.clock.tick(120)
        self.pg.mixer.music.stop()
        self.pg.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="?", type=Path,
                        help="a .osu/.osz file or a directory containing beatmaps")
    parser.add_argument("--difficulty", help="select a chart by difficulty name")
    args = parser.parse_args()
    paths: list[Path] = []
    if args.maps:
        if args.maps.is_file():
            paths = (list(p for p in extract_osz(args.maps) if is_native_4k(p))
                     if args.maps.suffix.lower() == ".osz"
                     else [args.maps])
        elif args.maps.is_dir():
            paths = sorted(p for p in args.maps.rglob("*.osu") if is_native_4k(p))
            for archive in sorted(args.maps.rglob("*.osz")):
                paths.extend(p for p in extract_osz(archive) if is_native_4k(p))
        else:
            parser.error(f"map path does not exist: {args.maps}")
    if args.maps and not paths:
        parser.error("no native 4K charts found")
    app = PlayableMania(paths)
    if args.difficulty:
        matches = [index for index, path in enumerate(paths)
                   if args.difficulty.casefold() in path.stem.casefold()]
        if len(matches) != 1:
            parser.error(f"expected one chart matching {args.difficulty!r}, found {len(matches)}")
        app.selected = matches[0]
    app.run()


if __name__ == "__main__":
    main()
