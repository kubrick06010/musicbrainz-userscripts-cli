# NTS Guide → MusicBrainz release-editor seeding

MusicBrainz does not expose a general public API for creating releases. Its documented integration path for third-party release importers is **Release Editor Seeding**: POST form fields to `https://musicbrainz.org/release/add`, then review and submit using the normal MusicBrainz UI.

`nts-guide-seed.py` implements that boundary.

Pipeline:

`NTS -> collector v3 -> candidate v1 -> local seed HTML -> MusicBrainz Add Release editor -> human review -> submit`

The seed generator never submits a MusicBrainz edit. The generated HTML contains a normal POST form and requires an explicit button click before MusicBrainz is opened.

## Generate a JSON candidate

```bash
python3 scripts/nts_guide_collector/nts-guide-candidate.py \
  japanese-techno-inventory.json \
  --episode the-nts-guide-to-90s-00s-japanese-techno-20th-august-2026 \
  --format json \
  -o japanese-techno-candidate.json
```

## Generate and open the seed page

```bash
python3 scripts/nts_guide_collector/nts-guide-seed.py \
  japanese-techno-candidate.json \
  -o japanese-techno-seed.html \
  --open
```

The local page displays a single **Open prefilled MusicBrainz editor** button. Clicking it POSTs the documented seed fields into the Add Release editor; it does not submit the release itself.

## Seeded fields

The v1 seeder maps candidate data to documented MusicBrainz release-editor seed fields:

- release title and status;
- release-group primary/secondary types;
- release date and country;
- NTS Radio label MBID;
- release artist credit and resolved MBIDs;
- Digital Media format;
- track titles, numbers, and NTS main-artist names;
- existing recording MBIDs only when the candidate already contains them;
- NTS source URL;
- an edit note identifying NTS as the source.

The seeder deliberately does **not** guess:

- barcode when NTS does not provide one;
- URL relationship link type;
- recording MBIDs;
- MBIDs for unresolved track artists;
- featured/remix artist-credit structure from NTS auxiliary arrays.

Those remain visible for review in the MusicBrainz editor.

## Safety gates

The seeder rejects candidates with `submission_ready: false`. There is no batch mode, no auto-submit JavaScript, no MusicBrainz edit POST, and no automatic final confirmation.
