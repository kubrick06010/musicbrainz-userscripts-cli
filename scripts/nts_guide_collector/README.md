# NTS Guide collector

Read-only collector/preflight tool for turning the complete NTS **NTS Guide to…** episode archive into a structured dataset suitable for reviewed MusicBrainz entry.

It deliberately does **not** submit edits.

## Goal

Coverage first, enrichment later.

The v3 schema separates whether a release can be safely created from whether all optional metadata has been enriched:

`NTS -> canonical inventory -> MusicBrainz duplicate safety -> CREATABLE / BLOCKED`

Optional mixer/compiler resolution, tracklist completeness and artwork enrichment are reported independently.

## Usage

Full archive:

```bash
python3 scripts/nts_guide_collector/nts-guide-collector.py -o nts-guide-inventory.json
```

The collector prints live progress to `stderr` by default, including current episode, CREATABLE/BLOCKED state, enrichment state, elapsed time and ETA. Final JSON/stdout remains machine-readable.

Example progress:

```text
[NTS] discovered 426 episodes; processing 426
[  1/426] processing the-nts-guide-to-example-1st-january-2026
[  1/426] CREATABLE | enrich PENDING  | elapsed 00:03 | ETA 21:15 | NTS Guide to: Example
...
[DONE] 426 episodes | CREATABLE 416 | BLOCKED 10 | elapsed 18:42
```

Suppress progress for automation:

```bash
python3 scripts/nts_guide_collector/nts-guide-collector.py --quiet -o nts-guide-inventory.json
```

### Single episode

When working on one release, do not scan the full archive. Pass the exact NTS episode alias:

```bash
python3 scripts/nts_guide_collector/nts-guide-collector.py \
  --episode the-nts-guide-to-90s-00s-japanese-techno-20th-august-2026 \
  -o japanese-techno-inventory.json
```

`--episode` fetches and classifies only that episode and is mutually exclusive with `--max-episodes`.

Small live smoke test:

```bash
python3 scripts/nts_guide_collector/nts-guide-collector.py --max-episodes 5 -o nts-guide-smoke.json
```

Collect source data without MusicBrainz lookups:

```bash
python3 scripts/nts_guide_collector/nts-guide-collector.py --no-musicbrainz -o nts-guide-inventory.json
```

When duplicate checking is disabled, releases remain blocked for creation because duplicate safety has not been established.

## MusicBrainz preflight

When MB lookups are enabled the collector:

- extracts explicit selector/mixer/compiler credits when NTS supplies them;
- supports obvious deterministic variants such as `selected & mixed by`, `compiled by`, `selections by`, and `words and selections by`;
- preserves the original raw credit text;
- splits plainly plural credits such as `Selected by A and B` into separate enrichment candidates without aggressively splitting ambiguous names;
- resolves credited people against MusicBrainz conservatively;
- searches for possible duplicate releases by title/date;
- distinguishes a successful zero-result search from an exhausted transient MusicBrainz failure;
- optionally reads an OAuth access token from `.mb_token.json` or `--mb-token-file`;
- retries transient HTTP `429`, `500`, `502`, `503`, and `504` responses with bounded backoff and reports retries on `stderr`;
- seeds the NTS Radio label MBID `2528f939-28ca-4da6-86c9-c6aab7bc4bc2`;
- proposes `Official`, `Digital Media`, `Worldwide`, and `Broadcast + DJ-mix` as reviewable MusicBrainz fields;
- never submits an edit.

## v3 status contract

Each episode has two independent status blocks.

### `creation_readiness`

- `CREATABLE`: enough NTS source metadata exists and MusicBrainz duplicate checking completed without finding a candidate.
- `BLOCKED`: creation is unsafe because a likely duplicate exists, duplicate checking failed transiently/was not run, or required identifying metadata is missing.

Missing optional mixer/compiler information does **not** block creation.

### `enrichment`

- `COMPLETE`: no currently tracked enrichment gaps remain.
- `PENDING`: one or more optional fields or relationships remain unresolved.

Examples include no explicit mixer credit, unresolved explicit credit, missing tracklist, missing artwork, or a transient artist lookup.

## Safety invariant

No MusicBrainz write endpoint exists in this module. The collector never invents absent metadata. Duplicate detection remains the hard safety gate; optional enrichment can happen later.

## Full-archive validation

The validated coverage-first run performed during development over 426 NTS Guide episodes produced:

- 416 `CREATABLE`
- 10 `BLOCKED`
- 3 convincing duplicate blocks
- 7 transient duplicate-check blocks
- 4 enrichment-complete episodes
- 422 enrichment-pending episodes
- 322 episodes without an explicit individual credit
- 38 unresolved explicit credits
- 15 episodes without a tracklist
- 426/426 with cover artwork available

The previous v2 classification was `15 READY / 373 REVIEW / 38 BLOCKED`; the validated v3 model therefore exposed 401 additional safely creatable releases without inventing metadata.

The generated 426-episode inventory is a validation artifact and is intentionally not committed to the repository. Regenerate it locally when fresh validation is needed.
