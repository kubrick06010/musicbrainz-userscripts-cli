# NTS Guide candidate builder

`nts-guide-candidate.py` converts one `CREATABLE` episode from an `nts-guide-collector/v3` inventory into a read-only MusicBrainz candidate.

It does not submit edits.

## Why it exists

The collector answers whether an NTS Guide episode is safe to represent. The candidate builder answers what we would try to create, while keeping required unknowns explicit instead of guessing.

Pipeline:

`NTS -> collector v3 -> CREATABLE episode -> candidate v1 -> human review -> future submitter`

## Usage

```bash
python3 scripts/nts_guide_collector/nts-guide-candidate.py \
  nts-guide-inventory.json \
  --episode the-nts-guide-to-90s-00s-japanese-techno-20th-august-2026
```

JSON output:

```bash
python3 scripts/nts_guide_collector/nts-guide-candidate.py \
  nts-guide-inventory.json \
  --episode the-nts-guide-to-90s-00s-japanese-techno-20th-august-2026 \
  --format json \
  -o japanese-techno-candidate.json
```

## Candidate contract

The candidate preserves source-backed fields such as:

- release/release-group title;
- broadcast date as the proposed release date;
- Official status;
- Worldwide (`XW`);
- NTS Radio label and MBID;
- Digital Media format;
- Broadcast / DJ-mix secondary types currently modeled by the collector;
- NTS tracklist text and source artist names;
- resolved explicit DJ/compiler relationships;
- NTS URL;
- artwork source URL;
- NTS description, genres and audio references.

Every transformed field has a provenance entry.

## Required unknowns

The first candidate schema deliberately marks these as unresolved rather than guessing:

- MusicBrainz release/release-group `artist_credit`;
- release-group `primary_type`.

A resolved mixer/compiler relationship is not automatically a release artist credit.

Track source names are also preserved without inventing recording MBIDs.

Therefore a candidate can be valid for review while `submission_ready` is `false`.

## Safety

The candidate builder rejects episodes whose `creation_readiness.status` is not `CREATABLE`.

It contains no MusicBrainz write path and no authentication/submission code.
