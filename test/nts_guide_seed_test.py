#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "scripts" / "nts_guide_collector" / "nts-guide-seed.py"
spec = importlib.util.spec_from_file_location("nts_guide_seed", SCRIPT)
seed = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(seed)


def candidate():
    return {
        "schema": "nts-guide-candidate/v1",
        "submission_ready": True,
        "source": {"provider": "NTS", "url": "https://www.nts.live/example", "episode_alias": "example"},
        "release_group": {"title": "Example", "primary_type": "Broadcast", "secondary_types": ["DJ-mix"]},
        "release": {
            "title": "Example", "status": "Official", "date": "2026-08-19", "country": "XW",
            "label": {"name": "NTS Radio", "mbid": "2528f939-28ca-4da6-86c9-c6aab7bc4bc2"},
            "catalog_number": None, "barcode": None,
            "medium": {"format": "Digital Media", "tracks": [{
                "position": 1, "title": "O.Y.M.", "artist_names": ["Captain Funk"],
                "featuring_artist_names": [], "remix_artist_names": [], "recording_mbid": None,
                "artist_resolutions": [{"name": "Captain Funk", "canonical_name": "Captain Funk", "mbid": "11111111-1111-1111-1111-111111111111", "status": "resolved", "basis": "test"}],
            }]},
        },
        "artist_credit": {"artists": [{"name": "Carpainter", "mbid": "f4b124f0-fccf-4add-a144-011735edbd68", "credited_as": "Carpainter"}], "basis": "officially credited DJ-mixer"},
        "urls": [{"url": "https://www.nts.live/example", "source": "NTS"}],
        "required_unresolved": [],
    }


class NTSGuideSeedTest(unittest.TestCase):
    def fields(self, value=None):
        return dict(seed.build_seed_fields(value or candidate()))

    def test_seed_maps_core_release_fields(self):
        fields = self.fields()
        self.assertEqual(fields["name"], "Example")
        self.assertEqual(fields["status"], "official")
        self.assertEqual(fields["events.0.date.year"], "2026")
        self.assertEqual(fields["events.0.country"], "XW")
        self.assertEqual(fields["labels.0.mbid"], "2528f939-28ca-4da6-86c9-c6aab7bc4bc2")
        self.assertEqual(fields["artist_credit.names.0.mbid"], "f4b124f0-fccf-4add-a144-011735edbd68")

    def test_seed_repeats_release_group_types(self):
        types = [value for name, value in seed.build_seed_fields(candidate()) if name == "type"]
        self.assertEqual(types, ["Broadcast", "DJ-mix"])

    def test_seed_maps_track_artist_mbid_without_inventing_recording(self):
        fields = self.fields()
        self.assertEqual(fields["mediums.0.track.0.artist_credit.names.0.name"], "Captain Funk")
        self.assertEqual(fields["mediums.0.track.0.artist_credit.names.0.mbid"], "11111111-1111-1111-1111-111111111111")
        self.assertNotIn("mediums.0.track.0.recording", fields)

    def test_unresolved_track_artist_is_rejected_by_default(self):
        value = candidate()
        value["release"]["medium"]["tracks"][0]["artist_resolutions"] = []
        with self.assertRaises(ValueError):
            seed.build_seed_fields(value)

    def test_allow_unresolved_track_artist_keeps_manual_name_seed(self):
        value = candidate()
        value["release"]["medium"]["tracks"][0]["artist_resolutions"] = []
        fields = dict(seed.build_seed_fields(value, require_resolved_track_artists=False))
        self.assertNotIn("mediums.0.track.0.artist_credit.names.0.mbid", fields)
        self.assertEqual(fields["mediums.0.track.0.artist_credit.names.0.artist.name"], "Captain Funk")

    def test_resolve_track_artists_records_mbid(self):
        value = candidate()
        value["release"]["medium"]["tracks"][0].pop("artist_resolutions")
        with patch.object(seed, "resolve_track_artist", return_value={"status": "resolved", "name": "Captain Funk", "mbid": "22222222-2222-2222-2222-222222222222", "basis": "unique exact artist name"}):
            resolved, unresolved = seed.resolve_track_artists(value, progress=False)
        self.assertEqual(unresolved, [])
        self.assertEqual(resolved["release"]["medium"]["tracks"][0]["artist_resolutions"][0]["mbid"], "22222222-2222-2222-2222-222222222222")

    def test_alias_match_resolves_canonical_artist(self):
        hit = {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "name": "石野卓球", "score": 100, "aliases": [{"name": "Takkyu Ishino"}]}
        with patch.object(seed, "_mb_search", return_value=[hit]), patch.object(seed, "_mb_artist", return_value=hit):
            result = seed.resolve_track_artist("Takkyu Ishino", "Feeling")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["name"], "石野卓球")
        self.assertEqual(result["mbid"], hit["id"])

    def test_aka_credit_can_resolve_one_side(self):
        hit = {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "name": "Susumu Yokota", "score": 100, "aliases": [{"name": "Ringo"}]}
        def fake_search(entity, query, limit=10, progress=False):
            return [hit] if entity == "artist" and ("Ringo" in query or "Susumu Yokota" in query) else []
        with patch.object(seed, "_mb_search", side_effect=fake_search), patch.object(seed, "_mb_artist", return_value=hit):
            result = seed.resolve_track_artist("Ringo Aka Susumu Yokota", "Tsukushi (1995)")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["mbid"], hit["id"])

    def test_parenthetical_context_can_be_stripped(self):
        hit = {"id": "cccccccc-cccc-cccc-cccc-cccccccccccc", "name": "Brothers In Raw", "score": 100, "aliases": []}
        def fake_search(entity, query, limit=10, progress=False):
            return [hit] if entity == "artist" and 'artist:"Brothers In Raw"' in query else []
        with patch.object(seed, "_mb_search", side_effect=fake_search):
            result = seed.resolve_track_artist("Brothers In Raw (Tobynation & Mijk Van Dijk)", "Ach-So!")
        self.assertEqual(result["status"], "resolved")
        self.assertIn("parenthetical", result["basis"])

    def test_missing_barcode_is_not_seeded_as_none(self):
        self.assertNotIn("barcode", self.fields())

    def test_url_is_seeded_without_guessing_link_type(self):
        fields = self.fields()
        self.assertEqual(fields["urls.0.url"], "https://www.nts.live/example")
        self.assertNotIn("urls.0.link_type", fields)

    def test_not_submission_ready_candidate_is_rejected(self):
        value = candidate()
        value["submission_ready"] = False
        value["required_unresolved"] = [{"field": "artist_credit", "reason": "unresolved"}]
        with self.assertRaises(ValueError):
            seed.build_seed_fields(value)

    def test_html_requires_explicit_button_click(self):
        rendered = seed.render_html(candidate())
        self.assertIn('action="https://musicbrainz.org/release/add"', rendered)
        self.assertIn("Open prefilled MusicBrainz editor", rendered)
        self.assertNotIn("document.forms[0].submit()", rendered)


if __name__ == "__main__":
    unittest.main()
