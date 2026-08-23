# Luna MusicBrainz CLI Port Status

Legend: `[ ]` not started · `[~]` in progress · `[x]` complete · `[!]` blocked

## Bootstrap and analysis

- [x] Clone fork and create `feat/cli-port` branch
- [x] Read and assess repository documentation and source areas
- [x] Create `docs/cli-port-analysis.md`
- [x] Create functional inventory and priority matrix

## Architecture and core

- [x] Create browser-independent TypeScript/ESM core
- [x] Extract normalization and matching logic
- [x] Define domain models and validation/errors
- [x] Implement MusicBrainz client with rate limiting, timeout, retry, cache
- [x] Implement provider adapters and provider-independent normalization
- [x] Create `docs/cli-architecture.md`

## CLI v0.1

- [x] Bootstrap `mbtool --help` and `mbtool --version`
- [x] Implement `release`
- [x] Implement `inspect`
- [x] Implement `isrc`
- [x] Implement `credits`
- [x] Implement `platforms`
- [x] Implement config, masked secrets, cache controls, output, exit codes

## Verification

- [x] Add unit, parser, fixture, matching, and CLI integration tests
- [x] Add CI for install, lint/typecheck, test, and build
- [x] Execute real-release smoke tests for all v0.1 commands
- [x] Create `docs/regression-report.md` with executed comparisons
- [x] Validate clean reproducibility
- [x] Perform final self-audit and placeholder review

## Documentation and delivery

- [x] Create `CLI_ROADMAP.md`
- [x] Update README without erasing upstream documentation
- [x] Create `CLI_PORT_REPORT.md`
- [x] Preserve GPL-3.0 notices and review git history/status
- [x] Completion gate: no `[ ]` or `[~]` entries remain
