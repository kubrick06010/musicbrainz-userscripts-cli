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

Existing MusicBrainz URL relationships are normalized for Discogs, Qobuz, Tidal, Deezer, Spotify, Bandcamp, Apple, Beatport, and SoundCloud. Deezer's public album endpoint is used for optional ISRC candidates when a Deezer album relationship is present. Other provider availability is conservative and reported as `UNVERIFIED` when no relationship or configured provider search is available; no provider failure is hidden as a match.

## Tests and executed validation

`npm install`, `npm run build`, `npm test`, `npm link`, `mbtool --help`, and `mbtool --version` all exited successfully. The test suite has 7 passing tests covering Unicode/punctuation normalization, ISRC validation, duration handling, confidence thresholds, help/version, invalid input, and masked configuration. Live commands were executed against release `aa6c4473-3528-41c2-b55b-d9e18bdba4ff` (The Exciting Sounds of Menahan Street Band): release, inspect, isrc, credits, platforms, all three requested provider filters, URL-form release, JSON output, and `jq` parse checks.

## Coverage

No line-coverage tool is configured yet. The current tests focus on deterministic core behavior and CLI smoke behavior; provider fixtures are derived from the upstream fixtures and the live release is used for MusicBrainz integration validation.

## Limitations and risks

Provider anti-bot systems, authentication requirements, regional catalogs, and incomplete MusicBrainz relationships can prevent discovery. The CLI reports these conditions instead of guessing. Provider credit search beyond existing links is intentionally conservative in v0.1. Cache files are local JSON and should not be used for secrets. MusicBrainz rate limits and transient failures can make uncached commands slower.

## Blockers

None. The upstream userscripts' browser test suites require their own Playwright/browser setup and are not a dependency of the CLI test workflow; the CLI has independent offline tests and live MusicBrainz smoke evidence.

## Future work outside v0.1

Additional authenticated provider adapters, stronger candidate search and track-level platform verification, ListenBrainz resolution, and explicit review-gated optional writes are tracked in `CLI_ROADMAP.md`.

## Commits

The work is on branch `feat/cli-port`. The repository history remains upstream history plus three focused commits: `c31de726 feat(cli): add browser-independent MusicBrainz CLI`, `b052f0e5 docs(cli): document architecture and validation`, and `b39b0bbd chore: close CLI port completion ledger`. No upstream files were mass-moved or cosmetically reformatted.

## Clean-checkout validation

`npm ci` was run successfully from the repository package manifest, followed by a successful build and 7-test suite. The final clean workflow is rerun immediately before delivery.
