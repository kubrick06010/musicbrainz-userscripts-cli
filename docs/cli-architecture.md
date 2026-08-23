# CLI Architecture

## Runtime flow

```text
MusicBrainz JSON / provider JSON
        ↓
HttpClient (fetch, User-Agent, timeout, retry, cache)
        ↓
MusicBrainzClient and provider adapters
        ↓
Release / Medium / Track / Relationship / PlatformLink models
        ↓
normalization + matching + validation
        ↓
CLI commands and JSON/human reporters
```

The root package is TypeScript ESM and emits `dist/`. The executable is `mbtool`. The existing userscripts remain in their original directories, which keeps the fork mergeable and leaves a future shared-core migration possible.

Provider adapters expose explicit capability declarations and normalize their results into `ProviderReleaseCandidate`, `ProviderTrackMetadata`, and `ProviderCredit`. Current adapters are Discogs (API release search/credits/platform verification), Qobuz (search/store-page credits/platform verification and token-gated album ISRC API), Tidal (token-gated search/credits/catalog ISRC API), and Deezer (public search/detail/platform/ISRC API).

## Browser independence

`src/core`, `src/providers`, and `src/shared` use no `document`, `window`, `location`, Greasemonkey/Tampermonkey APIs, DOM selectors, or browser automation. `HttpClient` is the CLI-side HTTP boundary. A future userscript adapter can implement an equivalent request boundary without moving provider and matching logic back into a page script.

## Domain models

`Release` contains normalized release identity, artist credits, media, tracks, MusicBrainz relationships, and platform links. `Track` contains recording identity, position, duration, artists, ISRCs, credits, and recording relationships. `ProviderMatch`, `PlatformLink`, and `MetadataConflict` keep provider evidence separate from the MusicBrainz model.

## Matching

Normalization applies Unicode compatibility decomposition, diacritic removal, case folding, punctuation cleanup, article handling for artists, and provider-safe ISRC normalization. Candidate scoring combines title, artist, track position, and duration with reproducible weights. Confidence is classified as `EXACT`, `HIGH`, `LIKELY`, `REVIEW`, or `REJECT`.

## Configuration and safety

Configuration is read from `$XDG_CONFIG_HOME/mbtool/config.json` or `~/.config/mbtool/config.json`; `MBTOOL_USER_AGENT` and `MBTOOL_DISCOGS_TOKEN` override file values. Cache data is stored below `$XDG_CACHE_HOME/mbtool` or `~/.cache/mbtool`. `config show` masks tokens. v0.1 has no write client, no `--apply`, and no browser automation.

## Exit codes

`0` success, `1` generic error, `2` invalid input/usage, `3` network error, `4` provider error, and `5` MusicBrainz error. JSON is written only to stdout; diagnostics are written to stderr.
