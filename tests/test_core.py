import unittest

from srt_subtitle_parser import Subtitle, parse_srt, serialize_srt


class TestParseSrt(unittest.TestCase):
    def test_basic_single_entry(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Hello, world!\n"
        )
        subs = parse_srt(content)
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0].start, 1000)
        self.assertEqual(subs[0].end, 4000)
        self.assertEqual(subs[0].text, "Hello, world!")

    def test_multiple_entries(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "First\n"
            "\n"
            "2\n"
            "00:00:03,000 --> 00:00:04,000\n"
            "Second\n"
        )
        subs = parse_srt(content)
        self.assertEqual(len(subs), 2)
        self.assertEqual(subs[0].text, "First")
        self.assertEqual(subs[1].text, "Second")

    def test_multiline_text(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "Line one\n"
            "Line two\n"
            "Line three\n"
        )
        subs = parse_srt(content)
        self.assertEqual(subs[0].text, "Line one\nLine two\nLine three")

    def test_period_as_subsecond_separator(self):
        # Some tools emit HH:MM:SS.mmm instead of HH:MM:SS,mmm.
        content = (
            "1\n"
            "00:00:01.500 --> 00:00:02.500\n"
            "Period separator\n"
        )
        subs = parse_srt(content)
        self.assertEqual(subs[0].start, 1500)
        self.assertEqual(subs[0].end, 2500)

    def test_crlf_line_endings(self):
        content = (
            "1\r\n"
            "00:00:01,000 --> 00:00:02,000\r\n"
            "CRLF line\r\n"
        )
        subs = parse_srt(content)
        self.assertEqual(subs[0].text, "CRLF line")

    def test_mixed_line_endings(self):
        content = (
            "1\r\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "Mixed\r\n"
        )
        subs = parse_srt(content)
        self.assertEqual(subs[0].text, "Mixed")

    def test_extra_blank_lines_between_entries(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "First\n"
            "\n"
            "\n"
            "\n"
            "2\n"
            "00:00:03,000 --> 00:00:04,000\n"
            "Second\n"
        )
        subs = parse_srt(content)
        self.assertEqual(len(subs), 2)

    def test_entry_without_index_line(self):
        # Some files omit the numeric index entirely.
        content = (
            "00:00:01,000 --> 00:00:02,000\n"
            "No index\n"
        )
        subs = parse_srt(content)
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0].text, "No index")

    def test_trailing_position_metadata_ignored(self):
        # Some SRT variants append X1/Y1/X2/Y2 coordinates after the timestamp.
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000 X1:50 X2:100 Y1:10 Y2:50\n"
            "Positioned\n"
        )
        subs = parse_srt(content)
        self.assertEqual(subs[0].start, 1000)
        self.assertEqual(subs[0].end, 2000)

    def test_empty_body_skipped(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "\n"
            "2\n"
            "00:00:03,000 --> 00:00:04,000\n"
            "Present\n"
        )
        subs = parse_srt(content)
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0].text, "Present")

    def test_invalid_timestamp_raises(self):
        content = (
            "1\n"
            "not a timestamp\n"
            "Bad\n"
        )
        with self.assertRaises(ValueError):
            parse_srt(content)

    def test_empty_input(self):
        self.assertEqual(parse_srt(""), [])

    def test_whitespace_only_input(self):
        self.assertEqual(parse_srt("   \n  \n  "), [])

    def test_trailing_whitespace_stripped_from_text_lines(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "Text with trailing space   \n"
        )
        subs = parse_srt(content)
        self.assertEqual(subs[0].text, "Text with trailing space")


class TestSerializeSrt(unittest.TestCase):
    def test_round_trip(self):
        original = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "Round trip\n"
            "\n"
            "2\n"
            "00:00:03,000 --> 00:00:04,500\n"
            "Second entry\n"
        )
        subs = parse_srt(original)
        serialized = serialize_srt(subs)
        reparsed = parse_srt(serialized)
        self.assertEqual(subs, reparsed)

    def test_indices_sequential_from_one(self):
        subs = [
            Subtitle(start=0, end=1000, text="A"),
            Subtitle(start=2000, end=3000, text="B"),
            Subtitle(start=4000, end=5000, text="C"),
        ]
        out = serialize_srt(subs)
        self.assertTrue(out.startswith("1\n"))
        self.assertIn("\n2\n", out)
        self.assertIn("\n3\n", out)

    def test_uses_comma_separator(self):
        subs = [Subtitle(start=1500, end=2500, text="X")]
        out = serialize_srt(subs)
        self.assertIn("00:00:01,500 --> 00:00:02,500", out)

    def test_no_trailing_blank_line(self):
        subs = [Subtitle(start=0, end=1000, text="A")]
        out = serialize_srt(subs)
        self.assertFalse(out.endswith("\n"))

    def test_empty_list_produces_empty_string(self):
        self.assertEqual(serialize_srt([]), "")


class TestSubtitleDataclass(unittest.TestCase):
    def test_end_before_start_raises(self):
        with self.assertRaises(ValueError):
            Subtitle(start=5000, end=1000, text="Bad")

    def test_negative_start_raises(self):
        with self.assertRaises(ValueError):
            Subtitle(start=-1, end=1000, text="Bad")

    def test_zero_duration_allowed(self):
        sub = Subtitle(start=1000, end=1000, text="Instant")
        self.assertEqual(sub.start, sub.end)

    def test_frozen(self):
        sub = Subtitle(start=0, end=1000, text="X")
        with self.assertRaises(Exception):
            sub.start = 5  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
