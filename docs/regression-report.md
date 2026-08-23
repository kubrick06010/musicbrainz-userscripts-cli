# Functional Regression Report

Behavioral equivalence here means that the CLI performs the same read-side external operation and returns materially comparable metadata; a command that only echoes MusicBrainz relationships is not counted as equivalent. The upstream source and fixtures were audited directly, and the CLI results below were executed live.

| Tool | Release | Provider | Upstream discovered metadata | CLI discovered metadata | Matched fields | Missing/extra | Equivalent? | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Credit Hoarder | `aa6c4473-3528-41c2-b55b-d9e18bdba4ff` | Discogs | Discogs release `17601142`; nested track and release credits | 28 provider credit rows; source URL and track positions retained | release ID, track titles/positions, role/name strings, source URL | CLI does not submit edits or resolve MB artist IDs | Yes, read-side | Discogs API is the native CLI transport alternative to the upstream browser request. |
| Credit Hoarder | `bca1db3d-9305-411d-b1ff-4a75e35aa1da` | Qobuz | Album `vft3hpnx5c3lc`; server-rendered per-track credit lines | 62 provider credit rows; 39 missing from MB; source URL retained | album ID, 16 track positions, credit names and roles | API artist IDs not attached to name-only store-page credits | Yes, read-side | The upstream parser's store-page path was reproduced with native HTTP. |
| Credit Hoarder | same Picó release | Tidal | Upstream uses rendered credits page and underlying authenticated endpoint | `AUTH_REQUIRED`; unauthenticated direct endpoint probe returned HTTP 401 | URL resolution and structured auth diagnostic | No anonymous external credits available in environment | Blocked by provider auth | Credential path is implemented; no secret was available to execute the authenticated branch. |
| ISRC Scout | `aa6c4473-3528-41c2-b55b-d9e18bdba4ff` | Deezer | Upstream resolves album and per-track public metadata | 14/14 real ISRC candidates; all match existing MB values | album ID, titles, positions, durations, ISRCs | No missing values on this release | Yes, read-side | Deezer's public track detail API provides the same ISRC evidence without a browser. |
| Platform Check | `aa6c4473-3528-41c2-b55b-d9e18bdba4ff` | Deezer | Upstream candidate search + album metadata verification | `FOUND`, album `183670242`, 14 tracks, score 1.00 | URL, title, artist, track count | Browser search fallback omitted | Yes, read-side | Public API candidate passed centralized release matching. |
| Platform Check | `bca1db3d-9305-411d-b1ff-4a75e35aa1da` | Qobuz | Existing/streaming Qobuz relationship and 16-track album | `EXISTING`, album `vft3hpnx5c3lc`, 16 tracks | URL, album ID, track count | No write/review UI | Yes, read-side | Store page was fetched and verified. |
| Platform Check | same Picó release | Discogs | Existing Discogs master/release relationship | Existing master resolved to main release `34327675`; 16-track comparison | provider URL and resolved API metadata | Master/release edition differences remain visible as conflict risk | Partial | API resolution works, but the master-to-release edition can differ from the MB release. |

## Offline regression evidence

The provider fixture suite covers Discogs track/release credits, Qobuz HTML credits and authenticated API ISRCs, Tidal contributors/ISRC-shaped tracks, Deezer detailed ISRCs, provider URL variants, malformed payloads, release scoring, and ISRC agreement/conflict. The final suite contains 16 passing tests and never requires live Internet access.

## Known limitations

Tidal credits/catalog and Qobuz `album/get` ISRC metadata require credentials; both paths are implemented and return structured `AUTH_REQUIRED` diagnostics when credentials are absent. Discogs HTML is Cloudflare-protected, so the CLI uses the public Discogs API. Discogs is not advertised as an ISRC provider because the upstream read-side path does not expose a reliable ISRC field.
