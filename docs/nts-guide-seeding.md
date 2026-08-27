# NTS Guide → MusicBrainz release-editor seeding

MusicBrainz does not expose a general public API for creating releases. Its documented integration path for third-party release importers is **Release Editor Seeding**: POST form fields to `https://musicbrainz.org/release/add`, then review and submit using the normal MusicBrainz UI.

`nts-guide-seed.py` implements that boundary.

Pipeline:

`NTS -> collector v3 -> candidate v1 -> track-artist resolution -> local seed HTML -> MusicBrainz Add Release editor -> human review -> submit`

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

Before writing the HTML, the seeder resolves every NTS main track-artist name against MusicBrainz. A single high-confidence exact artist-name match is accepted. If multiple MusicBrainz artists share the same exact name, the seeder uses the track title plus artist name to disambiguate only when that identifies exactly one matching artist MBID.

Progress is printed while resolving tracks. If any track artist remains unresolved, the seeder stops and lists the affected tracks instead of generating a seed that would leave unmatched artist fields in the MusicBrainz Tracklist tab.

For deliberate manual review only, this gate can be relaxed:

```bash
python3 scripts/nts_guide_collector/nts-guide-seed.py \
  japanese-techno-candidate.json \
  -o japanese-techno-seed.html \
  --allow-unresolved-track-artists \
  --open
```

In that mode unresolved artists are seeded by name only and must be matched manually in MusicBrainz.

The local page displays a single **Open prefilled MusicBrainz editor** button. Clicking it POSTs the documented seed fields into the Add Release editor; it does not submit the release itself.

## Seeded fields

The seeder maps candidate data to documented MusicBrainz release-editor seed fields:

- release title and status;
- release-group primary/secondary types;
- release date and country;
- NTS Radio label MBID;
- release artist credit and resolved MBIDs;
- Digital Media format;
- track titles and numbers;
- NTS main track-artist names plus resolved MusicBrainz artist MBIDs;
- existing recording MBIDs only when the candidate already contains them;
- NTS source URL;
- an edit note identifying NTS as the source.

The MusicBrainz Release Editor uses `mediums.x.track.y.artist_credit.names.z.mbid` to associate a track artist with an existing MusicBrainz artist. Supplying only the textual name leaves the artist unmatched in the editor; the seeder therefore resolves and supplies these MBIDs before opening MusicBrainz whenever possible.

The seeder deliberately does **not** guess:

- barcode when NTS does not provide one;
- URL relationship link type;
- recording MBIDs;
- ambiguous or unsupported track-artist MBIDs;
- featured/remix artist-credit structure from NTS auxiliary arrays.

## Safety gates

The seeder rejects candidates with `submission_ready: false`. By default it also rejects candidates whose track artists cannot all be safely mapped to MusicBrainz. There is no batch mode, no auto-submit JavaScript, no MusicBrainz edit POST, and no automatic final confirmation.
