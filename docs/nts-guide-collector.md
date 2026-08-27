# NTS Guide collector v3 architecture

The NTS Guide collector is intentionally coverage-first and read-only.

## Design principle

Release creation safety and metadata enrichment are separate concerns.

A release can be `CREATABLE` even when optional mixer/compiler relationships, track artist matching, timestamps, or other enrichment remain pending. The collector must never invent metadata that NTS did not publish.

## Operational visibility

The collector emits live progress to `stderr` by default so long archive runs are observable without contaminating JSON/stdout. Progress includes current episode, CREATABLE/BLOCKED status, enrichment status, elapsed time and ETA. Transient MusicBrainz retries are also reported.

Use `--quiet` to suppress progress in automation.

For targeted work, `--episode <exact-alias>` bypasses archive pagination and processes only that NTS episode. This is the preferred mode when building or reviewing one MusicBrainz candidate. `--episode` and `--max-episodes` are mutually exclusive.

## Hard creation gates

Creation is blocked only when the release cannot be identified safely or duplicate safety has not been established. Current blockers include:

- missing release title;
- convincing MusicBrainz duplicate candidate;
- transient MusicBrainz failure during duplicate lookup;
- duplicate lookup intentionally not run.

Artist-credit enrichment failures do not block an otherwise safe release.

## Enrichment

The collector records optional work independently. Current pending reasons include:

- `no_explicit_mixer_credit`;
- `credit_is_nts_collective`;
- `unresolved_explicit_credit`;
- `artist_lookup_transient`;
- `artist_resolution_not_run`;
- `missing_tracklist`;
- `missing_cover_art`;
- `missing_broadcast_date`.

## Credit parsing

Only explicit deterministic wording from NTS is parsed. The collector supports common forms such as `selected and mixed by`, `selected & mixed by`, `mixed by`, `selected by`, `curated by`, `compiled by`, `selections by`, and `words and selections by`.

Plain plural credits such as `Selected by A and B` may be represented as separate enrichment candidates. Ambiguous group/affiliation text is preserved rather than aggressively split. Raw NTS wording is retained.

## MusicBrainz lookup semantics

A successful search with zero results and an exhausted transient HTTP failure are different states.

Duplicate lookup transient failures block creation because they cannot safely be interpreted as proof that no duplicate exists. Artist lookup transient failures only leave enrichment pending.

## Validated archive result

A full authenticated run over 426 NTS Guide episodes produced 416 `CREATABLE` and 10 `BLOCKED` episodes. Three blocks were convincing duplicates and seven were transient duplicate-check failures.

The generated full inventory is not committed. It is reproducible validation output and should remain outside source control.
