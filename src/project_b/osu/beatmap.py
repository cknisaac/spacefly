"""Strict loader for native, unmodded four-key osu!mania beatmaps."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
import tempfile
from zipfile import ZipFile

from .types import HoldNote, TapNote


@dataclass(frozen=True, slots=True)
class TimingPoint:
    time_us: int
    beat_length_ms: Decimal
    uninherited: bool
    effects: int

    @property
    def scroll_multiplier(self) -> Decimal:
        if self.uninherited or self.beat_length_ms >= 0:
            return Decimal(1)
        return Decimal(-100) / self.beat_length_ms


@dataclass(frozen=True, slots=True)
class ManiaBeatmap:
    path: Path
    sha256: str
    title: str
    artist: str
    creator: str
    version: str
    audio_path: Path
    od: Decimal
    notes: tuple[TapNote | HoldNote, ...]
    timing_points: tuple[TimingPoint, ...]
    hitsound_count: int
    custom_samples: tuple[tuple[str, Path], ...] = ()

    @property
    def tap_count(self) -> int:
        return sum(isinstance(note, TapNote) for note in self.notes)

    @property
    def hold_count(self) -> int:
        return sum(isinstance(note, HoldNote) for note in self.notes)

    @property
    def end_time_us(self) -> int:
        return max((note.end_time_us if isinstance(note, HoldNote) else note.time_us)
                   for note in self.notes)


def _number(value: str, label: str, line: int) -> Decimal:
    try:
        parsed = Decimal(value.strip())
    except InvalidOperation as exc:
        raise ValueError(f"line {line}: invalid {label}: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"line {line}: nonfinite {label}")
    return parsed


def _time_us(value: str, label: str, line: int, *, allow_negative: bool = False) -> int:
    parsed = _number(value, label, line) * 1000
    if parsed != parsed.to_integral_value():
        raise ValueError(f"line {line}: {label} cannot be represented in microseconds")
    result = int(parsed)
    if result < 0 and not allow_negative:
        raise ValueError(f"line {line}: negative {label}")
    return result


def load_mania_beatmap(path: str | Path) -> ManiaBeatmap:
    """Load an osu!mania 4K file, rejecting objects we cannot reproduce.

    No object is silently converted, skipped, or replaced with a tap.
    """
    source = Path(path).resolve()
    raw = source.read_bytes()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Legacy .osu files can use a local 8-bit encoding.
        content = raw.decode("cp1252")
    sections: dict[str, list[tuple[int, str]]] = {}
    section = ""
    for line_number, raw_line in enumerate(content.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            sections.setdefault(section, [])
        elif section:
            sections[section].append((line_number, line))

    def fields(name: str) -> dict[str, str]:
        output = {}
        for _, row in sections.get(name, []):
            if ":" in row:
                key, value = row.split(":", 1)
                output[key.strip()] = value.strip()
        return output

    general = fields("General")
    difficulty = fields("Difficulty")
    metadata = fields("Metadata")
    if general.get("Mode") != "3":
        raise ValueError("only native osu!mania maps (Mode: 3) are supported")
    if _number(difficulty.get("CircleSize", ""), "CircleSize", 0) != 4:
        raise ValueError("only native 4K maps are supported")
    od = _number(difficulty.get("OverallDifficulty", ""), "OverallDifficulty", 0)
    if not Decimal(0) <= od <= Decimal(10):
        raise ValueError("OverallDifficulty must be in 0..10")
    audio_name = general.get("AudioFilename", "")
    if not audio_name:
        raise ValueError("map has no AudioFilename")
    audio_path = (source.parent / audio_name).resolve()
    if not audio_path.is_relative_to(source.parent) or not audio_path.is_file():
        raise ValueError(f"map audio is missing or outside its folder: {audio_name}")

    timing = []
    for line_number, row in sections.get("TimingPoints", []):
        parts = row.split(",")
        if len(parts) < 2:
            raise ValueError(f"line {line_number}: malformed timing point")
        uninherited = len(parts) < 7 or parts[6].strip() != "0"
        timing.append(TimingPoint(_time_us(parts[0], "timing point time", line_number,
                                           allow_negative=True),
                                  _number(parts[1], "beat length", line_number),
                                  uninherited,
                                  int(parts[7]) if len(parts) > 7 else 0))
    timing.sort(key=lambda point: point.time_us)
    if not timing:
        raise ValueError("map has no timing points")

    notes: list[TapNote | HoldNote] = []
    hitsound_count = 0
    custom_samples: list[tuple[str, Path]] = []
    for line_number, row in sections.get("HitObjects", []):
        parts = row.split(",")
        if len(parts) < 5:
            raise ValueError(f"line {line_number}: malformed hit object")
        x = _number(parts[0], "x", line_number)
        object_type = int(parts[3])
        lane = max(0, min(3, int(x // 128)))
        start = _time_us(parts[2], "object time", line_number)
        note_id = f"object-{len(notes)}"
        sample_field = parts[5] if len(parts) > 5 else ""
        sample_parts = sample_field.split(":", 5)
        custom_name = sample_parts[-1].strip() if len(sample_parts) >= 5 else ""
        if int(parts[4]) != 0 or custom_name or any(
                value not in ("", "0") for value in sample_parts[1:4]):
            hitsound_count += 1
        if custom_name:
            sample_path = (source.parent / custom_name).resolve()
            if sample_path.is_relative_to(source.parent) and sample_path.is_file():
                custom_samples.append((note_id, sample_path))
        if object_type & 128:
            if len(parts) < 6:
                raise ValueError(f"line {line_number}: long note lacks end time")
            end = _time_us(parts[5].split(":", 1)[0], "long-note end", line_number)
            if end <= start:
                raise ValueError(f"line {line_number}: long note has nonpositive duration")
            notes.append(HoldNote(note_id, lane, start, end))
        elif object_type & 1:
            notes.append(TapNote(note_id, lane, start))
        else:
            raise ValueError(f"line {line_number}: unsupported hit object type {object_type}")
    if not notes:
        raise ValueError("map has no hit objects")
    notes.sort(key=lambda note: (note.time_us, note.lane, note.note_id))
    return ManiaBeatmap(source, sha256(raw).hexdigest(), metadata.get("TitleUnicode") or
                        metadata.get("Title", source.stem), metadata.get("ArtistUnicode") or
                        metadata.get("Artist", ""), metadata.get("Creator", ""),
                        metadata.get("Version", ""), audio_path, od, tuple(notes),
                        tuple(timing), hitsound_count, tuple(custom_samples))


def extract_osz(path: str | Path) -> tuple[Path, ...]:
    """Extract a beatmap package to a validated, content-addressed temp cache."""
    source = Path(path).resolve()
    digest = sha256(source.read_bytes()).hexdigest()
    root = Path(tempfile.gettempdir()) / "spacefly-mania-beatmaps" / digest
    marker = root / ".complete"
    if marker.is_file():
        return tuple(sorted(root.rglob("*.osu")))
    if root.exists():
        # An interrupted extraction is never trusted or reused.
        root = root.with_name(f"{digest}-{sha256(str(source).encode()).hexdigest()[:10]}")
        if (root / ".complete").is_file():
            return tuple(sorted(root.rglob("*.osu")))
        if root.exists():
            raise ValueError(f"incomplete beatmap cache at {root}")
    root.mkdir(parents=True)
    total_size = 0
    with ZipFile(source) as archive:
        for member in archive.infolist():
            name = member.filename.replace("\\", "/")
            parts = Path(name).parts
            if not parts or name.startswith("/") or any(part in ("", ".", "..") for part in parts) or ":" in name:
                raise ValueError(f"unsafe package entry: {name}")
            if member.is_dir():
                continue
            total_size += member.file_size
            if total_size > 1_000_000_000 or member.file_size > 500_000_000:
                raise ValueError("beatmap package exceeds extraction limit")
            destination = (root / name).resolve()
            if not destination.is_relative_to(root):
                raise ValueError(f"unsafe package entry: {name}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as incoming, destination.open("wb") as outgoing:
                while block := incoming.read(1024 * 1024):
                    outgoing.write(block)
    maps = tuple(sorted(root.rglob("*.osu")))
    if not maps:
        raise ValueError("beatmap package contains no .osu files")
    marker.write_text(digest, encoding="ascii")
    return maps


def is_native_4k(path: str | Path) -> bool:
    """Cheap library filter; the full loader still validates the map on play."""
    try:
        raw = Path(path).read_bytes()
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = raw.decode("cp1252")
    except OSError:
        return False
    section = ""
    mode = None
    keys = None
    for row in content.splitlines():
        line = row.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif ":" in line:
            key, value = (part.strip() for part in line.split(":", 1))
            if section == "General" and key == "Mode":
                mode = value
            elif section == "Difficulty" and key == "CircleSize":
                keys = value
    try:
        return mode == "3" and Decimal(keys or "") == 4
    except InvalidOperation:
        return False
