#!/usr/bin/env python3
import importlib.util
import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "scripts" / "nts_guide_collector" / "nts-guide-collector.py"
spec = importlib.util.spec_from_file_location("nts_guide_collector", SCRIPT)
collector = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(collector)


def episode(name="Example", description="", tracklist=None):
    return {
        "alias": "example-1st-january-2026",
        "name": name,
        "broadcast": "2026-01-01T12:00:00+00:00",
        "description": description,
        "media": {"picture_large": "https://example.invalid/cover.jpg"},
        "tracklist": tracklist if tracklist is not None else [{"title": "Track", "mainArtists": [{"name": "Artist"}]}],
    }


def classified_result(title="Example"):
    return {
        "nts": {"title": title, "cover_url": "https://example.invalid/cover.jpg"},
        "creation_readiness": {"status": "CREATABLE", "blockers": []},
        "enrichment": {"status": "COMPLETE", "pending": []},
    }


class NTSGuideCollectorTest(unittest.TestCase):
    def classify(self, ep, duplicate=None, resolution=None):
        duplicate = duplicate or {"lookup_status": "ok", "http_status": None, "found": False, "candidates": []}
        resolution = resolution or {
            "name": "Carpainter", "mbid": "f4b124f0-fccf-4add-a144-011735edbd68", "score": 100,
            "status": "resolved", "lookup_status": "ok", "candidates": []
        }
        with patch.object(collector, "episode_detail", return_value=ep), \
             patch.object(collector, "duplicate_search", return_value=duplicate), \
             patch.object(collector, "resolve_artist", return_value=resolution):
            return collector.classify(ep, True, "token")

    def test_carpainter_is_creatable_when_artist_resolves(self):
        result = self.classify(episode(description="Selected and mixed by Carpainter."))
        self.assertEqual(result["creation_readiness"]["status"], "CREATABLE")
        self.assertEqual(result["enrichment"]["status"], "COMPLETE")

    def test_missing_mixer_does_not_block_creation(self):
        result = self.classify(episode(name="NTS Guide to: Pete Seeger's Rainbow Quest"))
        self.assertEqual(result["creation_readiness"]["status"], "CREATABLE")
        self.assertIn("no_explicit_mixer_credit", result["enrichment"]["pending"])

    def test_plural_credit_is_split_before_resolution(self):
        credits = collector.extract_credits("Selected by Merten Kaatz and Attillah Springer.")
        self.assertEqual([credit["name"] for credit in credits], ["Merten Kaatz", "Attillah Springer"])
        self.assertEqual(credits[0]["raw"], "Selected by Merten Kaatz and Attillah Springer")

    def test_duplicate_blocks_creation(self):
        duplicate = {"lookup_status": "ok", "http_status": None, "found": True, "candidates": [{"title": "Example", "mbid": "x", "score": 100, "date": "2026-01-01"}]}
        result = self.classify(episode(), duplicate=duplicate)
        self.assertEqual(result["creation_readiness"]["status"], "BLOCKED")
        self.assertIn("possible_duplicate_release", result["creation_readiness"]["blockers"])

    def test_duplicate_transient_error_blocks_creation(self):
        duplicate = {"lookup_status": "transient_error", "http_status": 503, "found": None, "candidates": []}
        result = self.classify(episode(), duplicate=duplicate)
        self.assertEqual(result["creation_readiness"]["status"], "BLOCKED")
        self.assertIn("duplicate_check_transient", result["creation_readiness"]["blockers"])

    def test_artist_transient_error_keeps_release_creatable(self):
        resolution = {"name": "Carpainter", "mbid": None, "score": 0, "status": "transient_error", "lookup_status": "transient_error", "http_status": 503, "candidates": []}
        result = self.classify(episode(description="Selected and mixed by Carpainter."), resolution=resolution)
        self.assertEqual(result["creation_readiness"]["status"], "CREATABLE")
        self.assertIn("artist_lookup_transient", result["enrichment"]["pending"])

    def test_no_musicbrainz_keeps_duplicate_safety_blocked(self):
        ep = episode(description="Selected by NTS.")
        with patch.object(collector, "episode_detail", return_value=ep):
            result = collector.classify(ep, False, None)
        self.assertEqual(result["creation_readiness"]["status"], "BLOCKED")
        self.assertIn("duplicate_check_not_run", result["creation_readiness"]["blockers"])

    def test_single_episode_mode_bypasses_archive_index(self):
        with patch.object(collector, "classify", return_value=classified_result("Single episode")) as classify_mock, \
             patch.object(collector, "get_json", side_effect=AssertionError("archive index should not be fetched")):
            result = collector.collect("the-nts-guide-to", 50, True, "token", episode_alias="single-alias", progress=False)
        self.assertEqual(result["episode_count"], 1)
        self.assertEqual(result["coverage_counts"]["CREATABLE"], 1)
        classify_mock.assert_called_once()

    def test_progress_is_emitted_to_stderr(self):
        buffer = io.StringIO()
        with patch.object(collector, "classify", return_value=classified_result("Single episode")), redirect_stderr(buffer):
            collector.collect("the-nts-guide-to", 50, True, "token", episode_alias="single-alias", progress=True)
        output = buffer.getvalue()
        self.assertIn("single-episode mode", output)
        self.assertIn("[  1/1]", output)
        self.assertIn("CREATABLE", output)
        self.assertIn("[DONE]", output)


if __name__ == "__main__":
    unittest.main()
