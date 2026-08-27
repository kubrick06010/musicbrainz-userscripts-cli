#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "nts_guide_collector" / "nts-guide-candidate.py"
spec = importlib.util.spec_from_file_location("nts_guide_candidate", SCRIPT)
candidate_builder = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(candidate_builder)


def creatable_episode(description="Selected and mixed by Carpainter.", credits=None):
    if credits is None:
        credits = [{
            "raw": "Selected and mixed by Carpainter",
            "name": "Carpainter",
            "role": "dj-mixer",
            "confidence": 0.98,
            "resolution": {"name": "Carpainter", "mbid": "f4b124f0-fccf-4add-a144-011735edbd68", "status": "resolved", "lookup_status": "ok"},
        }]
    return {
        "nts": {
            "episode_alias": "the-nts-guide-to-90s-00s-japanese-techno-20th-august-2026",
            "url": "https://www.nts.live/example",
            "title": "NTS Guide to: '90s & '00s Japanese Techno",
            "broadcast": "2026-08-19T23:00:00+00:00",
            "description": description,
            "genres": ["Techno"],
            "cover_url": "https://example.invalid/cover.jpg",
            "mixcloud": "https://example.invalid/mixcloud",
            "audio_sources": [],
            "tracklist": [
                {"position": 1, "title": "O.Y.M.", "offset": 0, "main_artists": ["Captain Funk"], "featuring_artists": [], "remix_artists": []}
            ],
        },
        "credits": credits,
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
    def test_carpainter_candidate_is_submission_ready(self):
        candidate = candidate_builder.build_candidate(creatable_episode())
        self.assertTrue(candidate["submission_ready"])
        self.assertEqual(candidate["required_unresolved"], [])
        self.assertEqual(candidate["artist_credit"]["artists"][0]["mbid"], "f4b124f0-fccf-4add-a144-011735edbd68")

    def test_broadcast_is_primary_type_and_dj_mix_is_secondary(self):
        candidate = candidate_builder.build_candidate(creatable_episode())
        self.assertEqual(candidate["release_group"]["primary_type"], "Broadcast")
        self.assertEqual(candidate["release_group"]["secondary_types"], ["DJ-mix"])

    def test_resolved_dj_mixer_is_also_preserved_as_relationship(self):
        candidate = candidate_builder.build_candidate(creatable_episode())
        relationship = candidate["relationships"][0]
        self.assertEqual(relationship["type"], "dj-mixer")
        self.assertEqual(relationship["artist"]["mbid"], "f4b124f0-fccf-4add-a144-011735edbd68")

    def test_no_overall_credit_uses_various_artists_for_broadcast(self):
        candidate = candidate_builder.build_candidate(creatable_episode(description="Editorial NTS selection.", credits=[]))
        artist = candidate["artist_credit"]["artists"][0]
        self.assertEqual(artist["name"], "Various Artists")
        self.assertEqual(artist["mbid"], candidate_builder.VARIOUS_ARTISTS_MBID)
        self.assertTrue(candidate["submission_ready"])

    def test_unresolved_official_mixer_keeps_candidate_not_submission_ready(self):
        credits = [{
            "raw": "Selected and mixed by Example DJ", "name": "Example DJ", "role": "dj-mixer", "confidence": 0.98,
            "resolution": {"name": "Example DJ", "mbid": None, "status": "missing", "lookup_status": "ok"},
        }]
        candidate = candidate_builder.build_candidate(creatable_episode(credits=credits))
        self.assertFalse(candidate["submission_ready"])
        self.assertIsNone(candidate["artist_credit"])
        self.assertEqual(candidate["required_unresolved"][0]["field"], "artist_credit")

    def test_tracklist_is_preserved_without_inventing_recording_mbid(self):
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
