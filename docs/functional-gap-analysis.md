# Functional Gap Analysis — Completion Pass

This audit compares the CLI against the read-side provider paths in the upstream Credit Hoarder, ISRC Scout, and Platform Check sources. The userscripts remain the behavioral reference; browser UI and write paths are intentionally excluded from the CLI.

## Credit Hoarder

| Capability | Status | Evidence / implementation |
| --- | --- | --- |
| Discogs release URL parsing and resolution | PORTED | `src/providers/discogs.ts` resolves existing release/master links, master main releases, or Discogs API search candidates. |
| Discogs release metadata and tracklist | PORTED | Discogs release JSON is normalized into provider tracks with positions, durations, source URLs, and candidate evidence. |
| Discogs per-track/release credits | PORTED | `extraartists`, nested track credits, index/sub-track flattening, and normalized roles are emitted as `ProviderCredit`. |
| Qobuz store-page resolution | PORTED | Qobuz search and server-rendered album pages are fetched with native `fetch`. |
| Qobuz credit extraction and role normalization | PORTED | `track__info` lines follow the upstream segment/role parser behavior; main-artist roles are excluded and useful production/composition roles are retained. |
| Qobuz authenticated API credit path | PARTIALLY_PORTED | CLI uses the public store page by default; optional `MBTOOL_QOBUZ_TOKEN` API support is implemented for ISRCs, while structured artist IDs from `album/get` are not yet attached to credits. |
| Tidal credit retrieval | PARTIALLY_PORTED | The upstream v1 credits endpoint and flexible contributor parser are implemented; Tidal requires an access token or client credentials in this environment. |
| Missing-credit comparison | PORTED | `--missing` compares normalized provider name/role/track evidence against MusicBrainz relationships and returns only absent external credits. |
| Browser review/edit submission | WRITE_ONLY/BROWSER_ONLY | Remains in the userscript and is not part of v0.1. |

## ISRC Scout

| Capability | Status | Evidence / implementation |
| --- | --- | --- |
| MusicBrainz recording ISRC extraction | PORTED | Release recordings are normalized before comparison. |
| Deezer album search/detail/track ISRCs | PORTED | Public album search resolves candidates; per-track detail calls extract ISRCs and are matched centrally. |
| Qobuz `album/get` ISRCs | PARTIALLY_PORTED | Implemented with `MBTOOL_QOBUZ_TOKEN`; upstream also requires an authenticated Qobuz session for this path. |
| Tidal catalog ISRCs | PARTIALLY_PORTED | Implemented with `MBTOOL_TIDAL_ACCESS_TOKEN` or client credentials; unauthenticated public endpoints return HTTP 401. |
| Discogs ISRC discovery | NOT_PORTED | The upstream Credit Hoarder/Platform Check Discogs paths provide credits/platform metadata, not a reliable Discogs ISRC field. |
| Track matching and evidence | PORTED | Title, artist, position, and duration feed the central scoring engine; evidence is emitted per candidate. |
| Provider agreement/conflict | PORTED | Values are grouped per MusicBrainz track; repeated independent values raise `agreement`, differing values become `CONFLICT`. |
| MusicBrainz writes | WRITE_ONLY | Deliberately absent from the CLI. |

## Platform Check

| Capability | Status | Evidence / implementation |
| --- | --- | --- |
| Existing URL relationship normalization | PORTED | Provider links are normalized from release and release-group relationships. |
| Discogs external discovery and verification | PORTED | Discogs API search/release retrieval supplies candidate title/artist/track count evidence. |
| Qobuz external discovery and verification | PORTED | Qobuz search/store-page retrieval provides candidates and track counts. |
| Deezer external discovery and verification | PORTED | Public search/detail API provides candidate title/artist/count evidence. |
| Tidal external discovery and verification | PARTIALLY_PORTED | Search/detail path is implemented with credentials; existing links remain visible when the public API returns `AUTH_REQUIRED`. |
| Search-engine/browser fallback | BROWSER_ONLY | Upstream uses browser search engines and provider tabs for some providers. Native API/page alternatives are used where available; no hidden browser is introduced. |

## Current truth

The CLI is now a genuine external read-side port for Discogs, Qobuz store pages, and Deezer, with credential-gated Tidal support and credential-gated Qobuz/Tidal ISRC paths. It does not claim Discogs ISRC support or anonymous Tidal API support. Structured diagnostics distinguish `AUTH_REQUIRED`, `NO_MATCH`, `NETWORK_ERROR`, and parser failures.
