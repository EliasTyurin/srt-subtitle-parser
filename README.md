# srt-subtitle-parser

Parses and serializes SubRip (`.srt`) subtitle files into structured records with `start`, `end`, and `text` fields. Standard library only, no dependencies.

## Usage

```python
from srt_subtitle_parser import parse_srt, serialize_srt, Subtitle

# Parse an .srt file
srt_text = """1
00:00:01,000 --> 00:00:04,000
Hello, world!
"""
subtitles = parse_srt(srt_text)

for sub in subtitles:
    print(f"{sub.start}–{sub.end} ms: {sub.text}")

# Build and serialize
custom = [
    Subtitle(start=1000, end=4000, text="Hello, world!"),
    Subtitle(start=5000, end=8000, text="Goodbye."),
]
srt_text = serialize_srt(custom)
```

## Why this exists

Subtitle files are simple enough that reaching for a dependency feels excessive, but fiddly enough that hand-rolling a parser every time is error-prone. This library occupies that middle ground: one import, no install step, handles the common variations in the wild.

The trade-off is scope. This is not a subtitle editing toolkit. It does not re-time, shift, or merge entries. It parses text into records and serializes records back into text. That is the entire surface.

## Edge cases

- **Blank lines within subtitle text are not preserved.** A blank line is treated as the delimiter between entries. If a subtitle's body contains an intentional blank line, it will be split into separate (incomplete) entries. This matches the behaviour of most players, which also treat blank lines as delimiters.
- **Timestamp sub-second separators:** Both `,` (spec-compliant) and `.` (emitted by some tools) are accepted on parse. Serialization always uses `,`.
- **Line endings:** `\r\n`, `\n`, and mixed are all handled on parse. Serialization emits `\n`.
- **Index lines:** Parsed but discarded. Serialization emits sequential indices starting at 1.
- **Empty subtitle bodies** (timestamp line followed immediately by a blank line) are silently skipped.
- **Trailing position metadata** (e.g. `X1:50 Y1:10` after the timestamp) is ignored.

## API

- `Subtitle(start: int, end: int, text: str)` — frozen dataclass. `start` and `end` are millisecond offsets from the start of the media.
- `parse_srt(content: str) -> list[Subtitle]` — parse SRT-formatted text. Raises `ValueError` on an unparseable timestamp line.
- `serialize_srt(subtitles: list[Subtitle]) -> str` — serialize records back to SRT text.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

