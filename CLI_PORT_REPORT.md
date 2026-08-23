# CLI Port Report

## Repository analysis

The upstream fork is a GPL-3.0 userscript toolset with separate per-tool JavaScript packages. The priority tools were ISRC Scout, Credit Hoarder, and Platform Check. Their read-side parsing, normalization, provider, and relationship behavior was reviewed; their UI, GM runtime, popup, and edit-submit paths remain browser-facing.

## Architecture implemented

The root package is Node.js 20+ TypeScript ESM. `src/core` contains domain models, normalization, validation, scoring, and confidence classification. `src/providers/musicbrainz` contains a dedicated web-service client. `src/providers` contains provider-aware read-side inspection. `src/shared` contains native-fetch HTTP, cache, and config adapters. `src/cli` exposes the `mbtool` executable. No browser globals or browser automation are used by v0.1 paths.

## Upstream code reused and refactored

The implementation follows and documents the upstream ISRC regex/normalization behavior, the Credit Hoarder provider registry and role/relationship concepts, and Platform Check's provider/status model. The original userscript source and fixtures remain in place; the CLI core is intentionally separated instead of importing DOM-bound bundles.

## Browser-bound code that remains

The userscript UI, DOM selectors, page-context globals, GM storage/request adapters, popup/background-tab harvesting, editor integration, OAuth setup, and all MusicBrainz mutation flows remain under `userscripts/`. They are outside the read-only CLI core.

## Implemented commands

`mbtool --help`, `--version`, `release`, `inspect`, `isrc`, `credits`, `platforms`, and `config show` are implemented. Release identifiers accept raw MBIDs and MusicBrainz release URLs. All data commands support human-readable output and `--json`; `isrc` supports `--verbose` and `--provider`; credits supports `--provider` and `--missing`; all commands support `--no-cache`.

## Supported providers

Existing MusicBrainz URL relationships are normalized for the upstream provider vocabulary, while the functional external adapters in this pass are Discogs, Qobuz, Tidal, and Deezer. Deezer's public album and track endpoints provide real ISRC candidates; Qobuz store pages provide credits; Discogs API provides credits/platform metadata; Qobuz ISRC and Tidal catalog/credits paths are credential-gated. Other upstream providers remain outside the functional completion scope.

## Tests and executed validation

`npm ci`, `npm run typecheck`, `npm run build`, `npm test`, `npm link`, `mbtool --help`, and `mbtool --version` all exited successfully. The test suite has 17 passing tests covering core normalization/matching, provider parsers and URL resolution, Qobuz authenticated-API ISRC parsing, malformed payloads, ISRC agreement/conflict, and credential diagnostics. Live commands were executed against multiple releases: Discogs credits on `aa6c4473-3528-41c2-b55b-d9e18bdba4ff`, Qobuz credits and platform verification on `bca1db3d-9305-411d-b1ff-4a75e35aa1da`, Deezer ISRC/platform discovery, Tidal authentication behavior, JSON output, and `jq` parse checks.

## Coverage

No line-coverage tool is configured yet. The current tests focus on deterministic core behavior and CLI smoke behavior; provider fixtures are derived from the upstream fixtures and the live release is used for MusicBrainz integration validation.

## Limitations and risks

Provider anti-bot systems, authentication requirements, regional catalogs, and incomplete MusicBrainz relationships can prevent discovery. The CLI reports these conditions instead of guessing. Provider credit search beyond existing links is intentionally conservative in v0.1. Cache files are local JSON and should not be used for secrets. MusicBrainz rate limits and transient failures can make uncached commands slower.

## Blockers

None. The upstream userscripts' browser test suites require their own Playwright/browser setup and are not a dependency of the CLI test workflow; the CLI has independent offline tests and live MusicBrainz smoke evidence.

## Future work outside v0.1

Additional authenticated provider adapters, stronger candidate search and track-level platform verification, ListenBrainz resolution, and explicit review-gated optional writes are tracked in `CLI_ROADMAP.md`.

## Functional Completion Pass

The previous CLI skeleton mostly echoed MusicBrainz relationships and emitted placeholder provider candidates. This pass audited the upstream Credit Hoarder, ISRC Scout, and Platform Check provider paths and added genuine external read-side adapters.

Discogs now resolves release/master relationships, searches the Discogs API, retrieves release JSON, parses tracklists and nested/release credits, and verifies platform candidates. Qobuz now searches/fetches server-rendered store pages and parses per-track production/composition credits; its authenticated `album/get` path is available through `MBTOOL_QOBUZ_TOKEN` for ISRCs. Tidal now has credential-gated search, credits endpoint parsing, and catalog ISRC retrieval through `MBTOOL_TIDAL_ACCESS_TOKEN` or client credentials. Deezer now resolves public album candidates and fetches per-track detail records for real ISRCs.

External credits are compared against normalized MusicBrainz relationship names/roles, and `--missing` filters genuinely absent external credits. External ISRC candidates are matched by title, artist, position, and duration; repeated provider values produce agreement counts and differing values produce `CONFLICT`. Platform Check now returns `FOUND`, `EXISTING`, `CONFLICT`, `MISSING`, or `UNVERIFIED` based on external candidate evidence and track counts. `inspect` includes external missing credits, ISRC candidates/conflicts, platform findings, diagnostics, and actionable commands.

Provider parser fixtures and matching tests increased the suite from 7 to 17 tests, covering Discogs/Qobuz/Tidal/Deezer parsing, malformed payloads, URL variants, Qobuz authenticated-API ISRC parsing, release matching, ISRC agreement/conflict, and credential diagnostics. Live evidence is recorded in [docs/live-smoke-matrix.md](docs/live-smoke-matrix.md): Discogs returned 28 missing credits, Qobuz returned 62 credits/39 missing, Deezer returned 14 real ISRC matches and a verified external platform, and Qobuz/Deezer platform verification succeeded on the 16-track Picó release. Tidal was exercised and returned a concrete HTTP 401 authentication requirement; its credential path and diagnostics are implemented but no anonymous Tidal data is claimed.

Remaining limitations are provider-side: Qobuz ISRC API and Tidal catalog/credits require credentials, Discogs HTML is Cloudflare-protected so the API is used, and Discogs is not claimed as an ISRC provider because upstream does not expose a reliable read-side ISRC path there. See [functional gap analysis](docs/functional-gap-analysis.md) for the exact PORTED/PARTIALLY_PORTED/NOT_PORTED classification.

## Commits

The work is on branch `feat/cli-port`. The repository history remains upstream history plus focused commits: `c31de726 feat(cli): add browser-independent MusicBrainz CLI`, `b052f0e5 docs(cli): document architecture and validation`, `b39b0bbd chore: close CLI port completion ledger`, `77021ab8 feat(providers): add external credit ISRC and platform discovery`, `007eb6c3 docs: record functional provider completion evidence`, and `3bad62be docs: close functional completion pass ledger`. No upstream files were mass-moved or cosmetically reformatted.

## Clean-checkout validation

`npm ci` was run successfully from the repository package manifest, followed by successful typecheck, build, 17-test suite, link, CLI bootstrap, multi-release provider smoke commands, and JSON parsing. The worktree is clean after the focused commits.
