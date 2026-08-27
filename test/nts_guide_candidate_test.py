#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "nts_guide_collector" / "nts-guide-candidate.py"
spec = importlib.util.spec_from_file_location("nts_guide_candidate", SCRIPT)
candidate_builder = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(candidate_builder)


def creatable_episode():
    return {
        "nts": {
            "episode_alias": "the-nts-guide-to-90s-00s-japanese-techno-20th-august-2026",
            "url": "https://www.nts.live/example",
            "title": "NTS Guide to: '90s & '00s Japanese Techno",
            "broadcast": "2026-08-19T23:00:00+00:00",
            "description": "Selected and mixed by Carpainter.",
            "genres": ["Techno"],
            "cover_url": "https://example.invalid/cover.jpg",
            "mixcloud": "https://example.invalid/mixcloud",
            "audio_sources": [],
            "tracklist": [
                {"position": 1, "title": "O.Y.M.", "offset": 0, "main_artists": ["Captain Funk"], "featuring_artists": [], "remix_artists": []}
            ],
        },
        "credits": [
            {
                "raw": "Selected and mixed by Carpainter",
                "name": "Carpainter",
                "role": "dj-mixer",
                "confidence": 0.98,
                "resolution": {"name": "Carpainter", "mbid": "f4b124f0-fccf-4add-a144-011735edbd68", "status": "resolved", "lookup_status": "ok"},
            }
        ],
        "musicbrainz": {
            "release_title": "NTS Guide to: '90s & '00s Japanese Techno",
            "release_status": "Official",
            "release_group_secondary_types": ["Broadcast", "DJ-mix"],
            "format": "Digital Media",
            "country": "XW",
            "label": {"name": "NTS Radio", "mbid": "2528f939-28ca-4da6-86c9-c6aab7bc4bc2"},
            "catalog_number": None,
            "barcode": None,
            "external_urls": [{"url": "https://www.nts.live/example", "source": "NTS"}],
        },
        "creation_readiness": {"status": "CREATABLE", "blockers": []},
        "enrichment": {"status": "COMPLETE", "pending": []},
    }


class NTSGuideCandidateTest(unittest.TestCase):
    def test_build_candidate_keeps_required_unknowns_explicit(self):
        candidate = candidate_builder.build_candidate(creatable_episode())
        self.assertFalse(candidate["submission_ready"])
        fields = [item["field"] for item in candidate["required_unresolved"]]
        self.assertIn("artist_credit", fields)
        self.assertIn("release_group.primary_type", fields)

    def test_build_candidate_preserves_resolved_dj_mixer_relationship(self):
        candidate = candidate_builder.build_candidate(creatable_episode())
        relationship = candidate["relationships"][0]
        self.assertEqual(relationship["type"], "dj-mixer")
        self.assertEqual(relationship["artist"]["mbid"], "f4b124f0-fccf-4add-a144-011735edbd68")

    def test_build_candidate_preserves_tracklist_without_inventing_recording_mbid(self):
        candidate = candidate_builder.build_candidate(creatable_episode())
        track = candidate["release"]["medium"]["tracks"][0]
        self.assertEqual(track["artist_names"], ["Captain Funk"])
        self.assertIsNone(track["recording_mbid"])

    def test_blocked_episode_is_rejected(self):
        episode = creatable_episode()
        episode["creation_readiness"] = {"status": "BLOCKED", "blockers": ["possible_duplicate_release"]}
        with self.assertRaises(ValueError):
            candidate_builder.build_candidate(episode)

    def test_find_episode_accepts_exact_alias(self):
        inventory = {"episodes": [creatable_episode()]}
        result = candidate_builder.find_episode(inventory, "the-nts-guide-to-90s-00s-japanese-techno-20th-august-2026")
        self.assertEqual(result["nts"]["title"], "NTS Guide to: '90s & '00s Japanese Techno")


if __name__ == "__main__":
    unittest.main()
