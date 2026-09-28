"""Parse and serialize SubRip (.srt) subtitle files.

Design decisions (documented because they are not obvious from the spec):

1. Timestamps are stored as integers in milliseconds. SRT's own format is
   always `HH:MM:SS,mmm`, so millisecond integers are a lossless and
   arithmetic-friendly representation. We deliberately do NOT use datetime or
   timedelta objects: those invite timezone and leap-second confusion that is
   meaningless for a subtitle duration.

2. The parser is lenient about line endings (\r\n, \n, or mixed) because real
   .srt files in the wild are routinely mangled by editors and version control.
   It is strict about the timestamp format itself: the spec uses a comma as the
   sub-second separator, and some tools emit a period instead. We accept both,
   because rejecting a file over one character is hostile, but we always
   serialize with a comma to match the spec.

3. The numeric index line before each entry is parsed but discarded: SRT
   indices are frequently renumbered by editors and are not semantically
   meaningful. Serialization emits sequential indices starting at 1.

4. Blank lines between entries are tolerated in any quantity. A subtitle's
   text is the set of non-empty lines between the timestamp line and the next
   blank line (or EOF). This means a subtitle cannot contain a genuinely blank
   line in the middle of its text — we treat a blank line as a delimiter. This
   is the one real edge case users hit; it is documented in the README.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

_TIMESTAMP_RE = re.compile(
    r"^"
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})"  # start
    r"\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})"  # end
    r"(?:\s+.*)?"  # optional trailing coords/position metadata, ignored
    r"$"
)


def _to_ms(h: str, m: str, s: str, ms: str) -> int:
    return (
        int(h) * 3_600_000
        + int(m) * 60_000
        + int(s) * 1_000
        + int(ms)
    )


def _format_ts(ms: int) -> str:
    if ms < 0:
        raise ValueError(f"timestamp must be non-negative, got {ms}")
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms_part = divmod(rem, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms_part:03d}"


@dataclass(frozen=True)
class Subtitle:
    """A single subtitle entry.

    ``start`` and ``end`` are inclusive millisecond offsets from the beginning
    of the media. ``text`` is the subtitle's body with lines preserved as given
    (minus trailing whitespace on each line).
    """
    start: int
    end: int
    text: str

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"start must be non-negative, got {self.start}")
        if self.end < 0:
            raise ValueError(f"end must be non-negative, got {self.end}")
        if self.end < self.start:
            raise ValueError(
                f"end ({self.end}) must not precede start ({self.start})"
            )


def parse_srt(content: str) -> List[Subtitle]:
    """Parse SRT-formatted text into a list of :class:`Subtitle` records.

    Raises :class:`ValueError` on the first entry whose timestamp line cannot
    be parsed. Entries with no body text are skipped silently, matching the
    behaviour of common players.
    """
    # Normalize line endings so splitlines behaves predictably regardless of
    # whether the input came from a Windows or Unix source.
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    results: List[Subtitle] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        # Skip blank lines between entries.
        if not line:
            i += 1
            continue

        # If the line is all digits, treat it as an index and move to the next
        # line, which should be the timestamp. If it is NOT all digits, we still
        # try to interpret the current line as a timestamp — some files omit the
        # index entirely.
        if line.isdigit():
            i += 1
            if i >= n:
                break
            ts_line = lines[i].strip()
        else:
            ts_line = line

        match = _TIMESTAMP_RE.match(ts_line)
        if not match:
            raise ValueError(
                f"invalid timestamp line at entry {len(results) + 1}: {ts_line!r}"
            )

        g = match.groups()
        start = _to_ms(g[0], g[1], g[2], g[3])
        end = _to_ms(g[4], g[5], g[6], g[7])
        i += 1

        # Collect body lines until a blank line or EOF.
        body: List[str] = []
        while i < n and lines[i].strip() != "":
            body.append(lines[i].rstrip())
            i += 1

        text = "\n".join(body)
        if not text:
            # Empty subtitle body — skip, as most players do.
            continue

        results.append(Subtitle(start=start, end=end, text=text))

    return results


def serialize_srt(subtitles: List[Subtitle]) -> str:
    """Serialize a list of :class:`Subtitle` records to SRT-formatted text.

    The output uses ``\n`` line endings and a single blank line between entries,
    with no trailing blank line after the final entry. Indices are sequential
    starting at 1.
    """
    parts: List[str] = []
    for idx, sub in enumerate(subtitles, start=1):
        block = (
            f"{idx}\n"
            f"{_format_ts(sub.start)} --> {_format_ts(sub.end)}\n"
            f"{sub.text}"
        )
        parts.append(block)
    return "\n\n".join(parts)
