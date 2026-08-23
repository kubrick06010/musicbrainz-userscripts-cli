# Live Smoke Matrix

All commands below were executed from the CLI branch with native Node `fetch`; no browser automation was used. Provider rows include the actual result rather than treating `UNVERIFIED` as success.

| Tool | Provider | Release | Expected capability | Result |
| --- | --- | --- | --- | --- |
| credits | Discogs | `aa6c4473-3528-41c2-b55b-d9e18bdba4ff` — The Exciting Sounds of Menahan Street Band | Existing Discogs release, per-track credits, missing comparison | 28 external credit rows; `--missing` marked all 28 absent; diagnostic `OK`; release `17601142`. |
| credits | Qobuz | `bca1db3d-9305-411d-b1ff-4a75e35aa1da` — Edna Martinez Presents Picó | Qobuz server-rendered credits | 62 external credit rows; `--missing` returned 39; diagnostic `OK`; album `vft3hpnx5c3lc`. |
| credits | Tidal | same Picó release | Tidal credits endpoint | `AUTH_REQUIRED`; direct unauthenticated endpoint probe returned HTTP 401. Credential path is implemented via `MBTOOL_TIDAL_ACCESS_TOKEN` or client credentials. |
| isrc | Deezer | `aa6c4473-3528-41c2-b55b-d9e18bdba4ff` | Album/detail track ISRC extraction | 14/14 tracks returned real ISRC candidates; diagnostic `OK`; all matched existing MB ISRCs. |
| platforms | Deezer | same Menahan release | External search and track-count verification | `FOUND`, album `183670242`, 14 tracks, score 1.00. |
| platforms | Qobuz | Picó release | Existing/external album verification | `EXISTING`, album `vft3hpnx5c3lc`, 16/16 tracks. |
| platforms | Discogs | Picó release | Existing/master resolution and verification | Existing MB master resolved to release `34327675`; track count reported 16 for the release comparison. |
| platforms | Tidal | Picó release | Existing link handling | Existing MB link preserved; verification diagnostic `AUTH_REQUIRED`. |

## Provider limitations observed

Qobuz store pages are publicly fetchable and expose credits, but Qobuz `album/get` ISRC metadata requires an authenticated token. Tidal public credits/catalog endpoints returned HTTP 401 without credentials. Discogs HTML is Cloudflare-protected, so the CLI uses the public Discogs API instead. These are provider/environment limitations, not placeholder rows; each is preserved in JSON diagnostics.
