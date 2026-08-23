# CLI Port Analysis

## Repository shape

The fork is a GPL-3.0 MusicBrainz userscript repository. The root contains userscripts, shell utilities, Picard plugins, development tooling, and per-tool package files rather than one application workspace. The priority tools are `userscripts/isrc_scout`, `userscripts/credit_hoarder`, and `userscripts/platform_check`.

## Reusable code

ISRC Scout already has useful pure operations for ISRC normalization, validation, provider URL classification, recording-level relationship inspection, and track comparison. Credit Hoarder has Discogs URL parsing, tracklist flattening, role parsing/mapping, provider registries, and consolidation heuristics. Platform Check has platform URL classification, candidate verification, barcode/track-count comparison, and provider scanners.

The port keeps those browser-facing files intact and reimplements the small provider-independent subset in `src/core` so it can be tested without a DOM. The core equivalents are `normalizeText`, `normalizeArtist`, `normalizeTitle`, `normalizeDuration`, `normalizeIsrc`, `scoreCandidate`, and confidence classification.

## Browser and runtime boundaries

The userscripts are intentionally DOM-bound at their entrypoints. They use `document`, `window`, selectors, `MutationObserver`, page navigation, `GM_xmlhttpRequest`, GM storage, and in some cases popup/background tabs to work around provider anti-bot systems. ISRC Scout and Platform Check also contain large UI/rendering sections; Credit Hoarder has a review table and edit submission flow.

The CLI does not import those entrypoints and does not automate a browser. It uses native Node `fetch` through `HttpClient`, a MusicBrainz JSON client, optional provider requests, JSON/human reporters, and filesystem cache/config adapters. No v0.1 core module references browser globals or Greasemonkey APIs.

## Network and write behavior

The userscripts contain both read and write paths: ISRC submission/deletion and Credit Hoarder relationship submission are mutation operations. The CLI deliberately implements only MusicBrainz reads and provider discovery/inspection. It never submits edits. MusicBrainz requests use the web service, a descriptive User-Agent, timeout, retry-after handling, retry for transient server errors, and a one-day opt-in cache.

## Tool inventory

| Tool | Browser dependency | Provider dependency | Core reusable | CLI candidate | Priority |
| --- | --- | --- | --- | --- | --- |
| String Theory | DOM/userscript runtime | MusicBrainz page | Low | Low | Later |
| Apollo Editor | DOM/userscript runtime | MusicBrainz editor | Some parsing | No v0.1 | Later |
| Art Station | DOM/userscript runtime | image hosts/MusicBrainz | URL/image helpers | No v0.1 | Later |
| Credit Hoarder | DOM + GM runtime | Discogs, Qobuz, Tidal, Deezer, Metal Archives | role parsing, consolidation | Yes | 2 |
| Group Therapy | DOM/userscript runtime | MusicBrainz | relationship helpers | Later | Later |
| ISRC Scout | DOM + GM runtime | SoundExchange, Deezer, Spotify, Beatport, Tidal, Volumo, HDtracks, Qobuz | ISRC parsing/matching | Yes | 1 |
| Mammoth | DOM + GM storage | none | settings concepts | No | Later |
| Platform Check | DOM + GM runtime | Spotify, Discogs, Bandcamp, Deezer, Apple, Tidal, Qobuz and others | URL/status/matching | Yes | 3 |
| Scribe | DOM/userscript runtime | editor integration | serialization | No v0.1 | Later |
| Falcon | DOM + editor APIs | Harmony/MusicBrainz | entity mapping | No v0.1 | Later |
| Fusion | DOM + editor APIs | MusicBrainz | recording matching | Later | Later |
| Bandcamp Player Enhanced | page DOM | Bandcamp | none | No | Later |

## Risks and extraction strategy

Provider APIs vary in authentication and anti-bot behavior. v0.1 therefore treats provider absence as a first-class `MISSING`/`UNVERIFIED` result and uses existing MusicBrainz URL relationships as reliable evidence. Future provider adapters can implement the same normalized `ProviderMatch` shape without changing core matching or CLI commands. Optional write commands are kept outside the current client interface so adding authentication and review gates later is explicit.
