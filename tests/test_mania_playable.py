"""Long-note behavior and strict native map loading for the playable client."""

from pathlib import Path
from contextlib import contextmanager
import json
import unittest
from uuid import uuid4
from zipfile import ZipFile

from project_b.osu.beatmap import extract_osz, is_native_4k, load_mania_beatmap
from project_b.osu.config import OsuConfig
from project_b.osu.mania_game import ManiaGame
from project_b.osu.playable import ScrollMap
from project_b.osu.types import HoldNote, KeyAction, KeyActionKind, TapNote


CONFIG = OsuConfig(od=8, ruleset="lazer")
WORK = Path(__file__).resolve().parents[1] / "work"


@contextmanager
def map_fixture(contents: str):
    token = uuid4().hex
    audio = WORK / f"{token}.wav"
    source = WORK / f"{token}.osu"
    audio.write_bytes(b"sample")
    source.write_text(contents.replace("AUDIO_NAME", audio.name), encoding="utf-8")
    try:
        yield source
    finally:
        source.unlink(missing_ok=True)
        audio.unlink(missing_ok=True)


def action(ms: int, kind: KeyActionKind, lane: int = 0) -> KeyAction:
    return KeyAction(ms * 1000, lane, kind)


def hold_results(actions):
    game = ManiaGame([HoldNote("hold", 0, 1_500_000, 4_000_000)], CONFIG)
    for item in actions:
        game.apply_action(item)
    game.finish()
    return game


class ManiaPlayableTests(unittest.TestCase):
    def test_tap_behavior_matches_frozen_lazer_corpus(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "lazer_mvp_4k_score_scenarios.json"
        reference = Path(__file__).resolve().parent / "fixtures" / "lazer_mvp_4k_score_reference.json"
        scenarios = json.loads(fixture.read_text(encoding="utf-8"))["scenarios"]
        expected = json.loads(reference.read_text(encoding="utf-8"))["scenarios"]
        for scenario, observed in zip(scenarios, expected):
            with self.subTest(scenario=scenario["id"]):
                notes = [TapNote(row["id"], row["lane"], row["time_us"])
                         for row in scenario["notes"]]
                game = ManiaGame(notes, CONFIG)
                for row in scenario["actions"]:
                    game.apply_action(KeyAction(row["time_us"], row["lane"],
                                                KeyActionKind(row["kind"])))
                game.finish()
                expected_results = [(row["note_id"], row["result"])
                                    for row in observed["events"]
                                    if row["kind"] == "judgement"]
                self.assertEqual([(row.note_id, row.result) for row in game.results],
                                 expected_results)
                last_score = next(row["score"]["total_score"]
                                  for row in reversed(observed["events"])
                                  if row["kind"] == "judgement")
                self.assertEqual(game.score.snapshot().score, last_score)

    def test_correct_long_note_has_head_and_tail_perfect_and_full_score(self):
        game = hold_results([action(1500, KeyActionKind.DOWN),
                             action(4000, KeyActionKind.UP)])
        self.assertEqual([(r.component, r.result) for r in game.results],
                         [("head", "PERFECT"), ("tail", "PERFECT"),
                          ("body", "IGNORE_HIT"), ("parent", "IGNORE_HIT")])
        self.assertEqual(game.score.snapshot().score, 1_000_000)
        self.assertEqual(game.score.snapshot().combo, 2)

    def test_no_input_misses_both_scoring_parts(self):
        game = hold_results([])
        self.assertEqual([(r.component, r.result) for r in game.results],
                         [("head", "MISS"), ("tail", "MISS"),
                          ("parent", "IGNORE_MISS"), ("body", "COMBO_BREAK")])
        self.assertEqual(game.score.snapshot().judged_accuracy_objects, 2)
        self.assertEqual(game.score.snapshot().score, 0)

    def test_early_release_then_repress_caps_tail_to_meh(self):
        game = hold_results([action(1500, KeyActionKind.DOWN),
                             action(1510, KeyActionKind.UP),
                             action(2500, KeyActionKind.DOWN),
                             action(4000, KeyActionKind.UP)])
        self.assertEqual([(r.component, r.result) for r in game.results],
                         [("head", "PERFECT"), ("body", "COMBO_BREAK"),
                          ("tail", "MEH"), ("parent", "IGNORE_HIT")])
        self.assertEqual(game.score.snapshot().combo, 1)

    def test_tap_and_hold_chord_keeps_both_objects(self):
        notes = [HoldNote("hold", 0, 1_500_000, 2_000_000),
                 TapNote("tap", 1, 1_500_000)]
        game = ManiaGame(notes, CONFIG)
        for item in (action(1500, KeyActionKind.DOWN),
                     action(1500, KeyActionKind.DOWN, 1),
                     action(2000, KeyActionKind.UP)):
            game.apply_action(item)
        game.finish()
        self.assertEqual(game.resolved_objects, 2)
        self.assertEqual(game.score.snapshot().score, 1_000_000)

    def test_native_map_loads_all_taps_holds_and_timing_changes(self):
        with map_fixture(
                "osu file format v14\n[General]\nAudioFilename: AUDIO_NAME\nMode: 3\n"
                "[Metadata]\nTitle: Example\nArtist: Example Artist\n"
                "[Difficulty]\nCircleSize: 4\nOverallDifficulty: 8\n"
                "[TimingPoints]\n0,500,4,2,1,100,1,0\n1000,-50,4,2,1,100,0,0\n"
                "[HitObjects]\n64,192,1500,1,0,0:0:0:0:\n"
                "192,192,2000,128,0,3000:0:0:0:0:\n") as source:
            beatmap = load_mania_beatmap(source)
            self.assertTrue(is_native_4k(source))
            self.assertEqual((beatmap.tap_count, beatmap.hold_count), (1, 1))
            self.assertEqual(beatmap.end_time_us, 3_000_000)
            self.assertEqual(beatmap.timing_points[1].scroll_multiplier, 2)
            self.assertEqual([note.lane for note in beatmap.notes], [0, 1])
            self.assertEqual(beatmap.hitsound_count, 0)

    def test_unsupported_object_is_rejected_instead_of_dropped(self):
        with map_fixture(
                "[General]\nAudioFilename: AUDIO_NAME\nMode: 3\n"
                "[Difficulty]\nCircleSize: 4\nOverallDifficulty: 8\n"
                "[TimingPoints]\n0,500,4,2,1,100,1,0\n"
                "[HitObjects]\n64,192,1500,2,0,B|100:192,1,100\n") as source:
            with self.assertRaisesRegex(ValueError, "unsupported hit object"):
                load_mania_beatmap(source)

    def test_osz_package_opens_and_rejects_path_traversal(self):
        with map_fixture(
                "[General]\nAudioFilename: AUDIO_NAME\nMode: 3\n"
                "[Difficulty]\nCircleSize: 4\nOverallDifficulty: 8\n"
                "[TimingPoints]\n0,500,4,2,1,100,1,0\n"
                "[HitObjects]\n64,192,1500,1,0,0:0:0:0:\n") as source:
            archive = WORK / f"{uuid4().hex}.osz"
            bad_archive = WORK / f"{uuid4().hex}.osz"
            try:
                with ZipFile(archive, "w") as zipped:
                    zipped.write(source, source.name)
                    zipped.write(source.with_suffix(".wav"), source.with_suffix(".wav").name)
                maps = extract_osz(archive)
                self.assertEqual(len(maps), 1)
                self.assertEqual(load_mania_beatmap(maps[0]).tap_count, 1)
                with ZipFile(bad_archive, "w") as zipped:
                    zipped.writestr("../outside.osu", "invalid")
                with self.assertRaisesRegex(ValueError, "unsafe package entry"):
                    extract_osz(bad_archive)
            finally:
                archive.unlink(missing_ok=True)
                bad_archive.unlink(missing_ok=True)

    def test_scroll_base_uses_tempo_duration_not_point_count(self):
        with map_fixture(
                "[General]\nAudioFilename: AUDIO_NAME\nMode: 3\n"
                "[Difficulty]\nCircleSize: 4\nOverallDifficulty: 8\n"
                "[TimingPoints]\n0,500,4,2,1,100,1,0\n"
                "1000,250,4,2,1,100,1,0\n1100,250,4,2,1,100,1,0\n"
                "[HitObjects]\n64,192,1500,1,0,0:0:0:0:\n") as source:
            scroll = ScrollMap(load_mania_beatmap(source))
            # 500 ms dominates 0-1000 ms, whereas 250 has more points.
            self.assertEqual(scroll.position(500_000) - scroll.position(0), 500_000)
            self.assertEqual(scroll.position(1_200_000) - scroll.position(1_100_000),
                             200_000)

    def test_negative_timing_offset_is_accepted(self):
        with map_fixture(
                "[General]\nAudioFilename: AUDIO_NAME\nMode: 3\n"
                "[Difficulty]\nCircleSize: 4\nOverallDifficulty: 8\n"
                "[TimingPoints]\n-500,500,4,2,1,100,1,0\n"
                "[HitObjects]\n64,192,1500,1,0,0:0:0:0:\n") as source:
            beatmap = load_mania_beatmap(source)
            self.assertEqual(beatmap.timing_points[0].time_us, -500_000)
            self.assertEqual(ScrollMap(beatmap).position(0), 500_000)


if __name__ == "__main__":
    unittest.main()
