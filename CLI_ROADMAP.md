# CLI Roadmap

## v0.1 — read-only

- `release`, `inspect`, `isrc`, `credits`, and `platforms`
- MusicBrainz JSON client, normalized domain models, deterministic matching, cache, and JSON output

## v0.2

Add more provider adapters, improve provider authentication/configuration, expand fixture coverage, and tune matching quality and performance.

## v0.3 — ListenBrainz integration

Design `mbtool resolve "Artist - Track"` and `mbtool resolve --listenbrainz <listen>` around listen artist/title/album data, candidate search, MusicBrainz recording/release candidates, matching, and confidence. This remains read-only until review behavior is specified.

## v0.4 — optional writes

Potential `--apply` operations for ISRCs and credits must be explicit, authenticated, reviewable, and preferably support `--dry-run`. No write path is present in v0.1.

## v1.0

Stabilize CLI output and public core interfaces, then share the normalized provider/matching modules with browser-facing tooling where practical.
