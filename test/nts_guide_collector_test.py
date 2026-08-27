#!/usr/bin/env python3
import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
