# Regression Report

The source userscripts remain the behavioral reference. The comparisons below use the upstream fixture releases and the executed CLI behavior. The v0.1 CLI is intentionally read-only, so “equivalent” means the same read-side metadata is represented or the limitation is explicitly surfaced rather than silently guessed.

| Feature | Release | Userscript result | CLI result | Equivalent? | Difference/reason |
| --- | --- | --- | --- | --- | --- |
| ISRC Scout | Menahan Street Band — `aa6c4473-3528-41c2-b55b-d9e18bdba4ff` | Reads existing recording ISRCs and linked providers | `isrc` reads recording ISRCs and emits provider evidence/candidates | Yes for read-side | CLI does not submit values |
| Credit Hoarder | `18cae3db-fa2c-493e-8e53-803bed92b8a5` | Shows existing/derived relationship credits in review table | `credits` emits normalized MusicBrainz relationship rows | Yes for read-side | Provider credit discovery is conservative when provider APIs are unavailable |
| Platform Check | Menahan Street Band — `aa6c4473-3528-41c2-b55b-d9e18bdba4ff` | Shows existing Spotify/Discogs/Bandcamp links and provider statuses | `platforms` preserves existing links and marks unlinked providers `UNVERIFIED` | Yes for existing links | CLI does not use browser search fallback |

Execution evidence: `npm run build`, `npm test`, CLI help/version, invalid-input, JSON parsing, and live-release smoke commands were run during the port. Live provider availability is represented in output and is not treated as a write or a match.
