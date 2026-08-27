# NTS Guide candidate builder

`nts-guide-candidate.py` converts one `CREATABLE` episode from an `nts-guide-collector/v3` inventory into a read-only MusicBrainz candidate.

It does not submit edits.

## Why it exists

The collector answers whether an NTS Guide episode is safe to represent. The candidate builder answers what we would try to create and applies only deterministic MusicBrainz style rules.

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

The candidate preserves source-backed fields such as title, broadcast date, Official status, Worldwide (`XW`), NTS Radio label/MBID, Digital Media format, NTS tracklist text, resolved explicit relationships, NTS URL and artwork source URL.

Every transformed field has a provenance entry.

## MusicBrainz type normalization

MusicBrainz models `Broadcast` as a **primary** release-group type and `DJ-mix` as a secondary type. Older v3 inventories may contain both values in `release_group_secondary_types`; the candidate builder normalizes this to:

- primary type: `Broadcast`
- secondary type: `DJ-mix`

## Release artist credit

The candidate builder follows the MusicBrainz artist-credit style rules rather than inventing a credit:

- if NTS explicitly credits a DJ-mixer and that artist is safely resolved, the DJ-mixer becomes the proposed release/release-group artist credit;
- if NTS has no overall credited artist for the broadcast, the proposed credit is MusicBrainz's special-purpose `Various Artists` artist (`89ad4ac3-39f7-470e-963a-56509c546377`);
- if an explicitly credited DJ-mixer exists but cannot be safely resolved, `artist_credit` remains unresolved and `submission_ready` stays false.

Resolved DJ/compiler credits are also preserved as relationships; using a DJ-mixer as release artist does not remove the DJ-mixer relationship.

## Tracks

Track titles and source artist names are preserved from NTS. The builder does not invent recording MBIDs. Recording/track artist resolution remains a later enrichment/submission concern.

## Safety

The candidate builder rejects episodes whose `creation_readiness.status` is not `CREATABLE`.

It contains no MusicBrainz write path and no authentication/submission code.
