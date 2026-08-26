# NTS Guide collector

Read-only collector/preflight tool for turning the complete NTS **NTS Guide to…** episode archive into a structured dataset suitable for reviewed MusicBrainz entry.

It deliberately does **not** submit edits.

## Pipeline

`NTS -> canonical inventory -> MusicBrainz resolution/duplicate checks -> READY / REVIEW / BLOCKED -> future Scribe/Falcon payload`

## Usage

```bash
python3 scripts/nts_guide_collector/nts-guide-collector.py -o nts-guide-inventory.json
```

To collect NTS data without querying MusicBrainz:

```bash
python3 scripts/nts_guide_collector/nts-guide-collector.py --no-musicbrainz -o nts-guide-inventory.json
```

The collector paginates `/api/v2/shows/the-nts-guide-to/episodes`, then requests each episode as JSON. It preserves the NTS source URL, title, broadcast timestamp, location, description, genres, largest advertised picture, Mixcloud/audio sources and structured tracklist (`mainArtists`, `featuringArtists`, `remixArtists`, `offset`).

## MusicBrainz preflight

When MB lookups are enabled it:

- extracts explicit `selected and mixed by`, `mixed by`, `selected by`, and `curated by` credits;
- resolves credited people against MusicBrainz, retaining candidate MBIDs and scores rather than silently choosing ambiguous matches;
- searches for possible duplicate releases by title/date;
- seeds the known NTS Radio label MBID (`2528f939-28ca-4da6-86c9-c6aab7bc4bc2`);
- proposes `Official`, `Digital Media`, `Worldwide`, and `Broadcast + DJ-mix` as reviewable MusicBrainz fields;
- never submits an edit.

MusicBrainz requests are serialized with a delay to respect the public web-service rate guidance.

## Status contract

- `READY`: no blockers or warnings found by the current rules.
- `REVIEW`: usable source data but something needs a human decision (for example no explicit mixer credit or no tracklist).
- `BLOCKED`: an ambiguous/unresolved credited artist or possible duplicate prevents generation from being treated as safe.

`READY` is intentionally conservative. A later phase should add release-group matching, cover-art existence/hash checks, recording/track-artist resolution, relationship payloads, and Scribe/Falcon exporters before any submission path is considered.

## Safety invariant

No MusicBrainz write endpoint exists in this module. Adding submission support should be a separate explicit phase with dry-run diff and human confirmation.
