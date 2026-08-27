#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

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
            "medium": {"format": "Digital Media", "tracks": [
                {"position": 1, "title": "O.Y.M.", "artist_names": ["Captain Funk"], "featuring_artist_names": [], "remix_artist_names": [], "recording_mbid": None}
            ]},
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
        fields = seed.build_seed_fields(candidate())
        types = [value for name, value in fields if name == "type"]
        self.assertEqual(types, ["Broadcast", "DJ-mix"])

    def test_seed_maps_track_without_inventing_recording(self):
        fields = self.fields()
        self.assertEqual(fields["mediums.0.track.0.name"], "O.Y.M.")
        self.assertEqual(fields["mediums.0.track.0.artist_credit.names.0.name"], "Captain Funk")
        self.assertNotIn("mediums.0.track.0.recording", fields)

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
