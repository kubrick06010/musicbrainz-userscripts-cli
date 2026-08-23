# Musicbrainz Toolset

This repository contains tools ([userscripts](https://musicbrainz.org/doc/Guides/Userscripts), [picard plugins](https://picard-docs.musicbrainz.org/en/latest/extending/plugins.html) and [shell scripts](./scripts)) to be used with [MusicBrainz](https://musicbrainz.org).

> [!IMPORTANT]
>  [String Theory](./userscripts/string_theory/README.md) <img src="./userscripts/string_theory/icon.svg" align="left" width="32"><br>
One-file bundle of all of the scripts in section bellow — install it *instead* of individuall userscripts

<br>

[Apollo Editor](./userscripts/apollo_editor/README.md) <img src="./userscripts/apollo_editor/icon.svg" align="left" width="32"><br>
UI and tools for advanced adding and editing of MusicBrainz release

[Art Station](./userscripts/art_station/README.md) <img src="./userscripts/art_station/icon.png" align="left" width="32"><br>
Cover/event-art editor: view, reorder, retype, comment, remove, download, add source from Internet

[Credit Hoarder](./userscripts/credit_hoarder/README.md)<img src="./userscripts/credit_hoarder/icon.svg" align="left" width="32"><br>
Import credits from several providers with a review phase

[Group Therapy](./userscripts/group_therapy/README.md) <img src="./userscripts/group_therapy/icon.svg" align="left" width="32"><br>
Batch operations and various helpers for editing relationships

[ISRC Scout](./userscripts/isrc_scout/README.md)<img src="./userscripts/isrc_scout/icon.svg" align="left" width="32"><br>
Reads the release's existing ISRCs and streaming links and fills in the missing ones

[Mammoth](./userscripts/mammoth/README.md)<img src="./userscripts/mammoth/icon.svg" align="left" width="32"><br>
Remembers your edit notes and options and lets you save and recall them

[Platform Check](./userscripts/platform_check/README.md)<img src="./userscripts/platform_check/icon.svg" align="left" width="32"><br>
Find and verify URLs for a particular MusicBrainz release on online platforms

---

[Scribe](./userscripts/scribe/README.md) <img src="./userscripts/scribe/scribe.svg" align="left" width="32"><br>
Edit MusicBrainz in your real editor (VS Code, Vim, …)

[Falcon](./userscripts/falcon/README.md) <img src="./userscripts/falcon/icon.svg" align="left" width="32"><br>
Batch import entity fields from Harmony and standalone

[Fusion](./userscripts/fusion/README.md) <img src="./userscripts/fusion/icon.svg" align="left" width="32"><br>
Merge duplicate recordings: review UI, auto-match, background submit

---

[Bandcamp Player Enhanced](./userscripts/bandcamp_player_enhanced/README.md)<img src="./userscripts/bandcamp_player_enhanced/icon.svg" align="left" width="32"><br>
Bandcamp album player with keyboard shortcuts

## Browser-independent CLI

This fork also contains `mbtool`, a read-only Node.js CLI built on a browser-independent MusicBrainz client and normalized core models. The original userscripts remain available and their browser-bound behavior is preserved.

### Install and build

```bash
npm install
npm run build
npm test
npm link
```

### Usage

```bash
mbtool --help
mbtool --version
mbtool release <MBID-or-MusicBrainz-URL>
mbtool inspect <MBID> --json | jq .
mbtool isrc <MBID> --verbose
mbtool credits <MBID> --provider qobuz
mbtool credits <MBID> --missing --json
mbtool platforms <MBID> --json
mbtool config show
```

The CLI accepts raw release MBIDs and MusicBrainz release URLs. Normal output goes to stdout and diagnostics go to stderr. `--no-cache` disables the filesystem cache for a command. Configuration is read from `~/.config/mbtool/config.json` (or `$XDG_CONFIG_HOME/mbtool/config.json`); `MBTOOL_USER_AGENT`, `MBTOOL_DISCOGS_TOKEN`, `MBTOOL_QOBUZ_TOKEN`, `MBTOOL_TIDAL_ACCESS_TOKEN`, `MBTOOL_TIDAL_CLIENT_ID`, and `MBTOOL_TIDAL_CLIENT_SECRET` are supported environment overrides. Discogs, Qobuz store pages, and Deezer are usable without provider credentials; Qobuz ISRC API and Tidal catalog/credits require provider credentials. v0.1 never edits MusicBrainz.

Provider capabilities and live evidence are documented in [functional gap analysis](docs/functional-gap-analysis.md) and [live smoke matrix](docs/live-smoke-matrix.md). Provider errors are retained in JSON diagnostics as `NO_MATCH`, `AUTH_REQUIRED`, `RATE_LIMITED`, `NETWORK_ERROR`, `PARSER_ERROR`, or related statuses.

Exit codes are 0 success, 1 generic error, 2 invalid input, 3 network error, 4 provider error, and 5 MusicBrainz error. See [CLI architecture](docs/cli-architecture.md) and [roadmap](CLI_ROADMAP.md).
