#!/usr/bin/env node
import { HttpClient } from '../shared/http.js';
import { maskedConfig, readConfig } from '../shared/config.js';
import { MbToolError } from '../core/errors.js';
import { MusicBrainzClient } from '../providers/musicbrainz/client.js';
import { inspectCredits, inspectIsrc, inspectPlatforms } from '../providers/index.js';
import type { Release } from '../core/models.js';

const VERSION = '0.1.0';
const HELP = `mbtool ${VERSION} — read-only MusicBrainz metadata tools

Usage: mbtool <command> <MBID-or-URL> [options]

Commands:
  release <release>       Show release metadata and track listing
  inspect <release>       Show aggregate metadata health
  isrc <release>          Inspect ISRC coverage and provider candidates
  credits <release>       Inspect MusicBrainz credits and relationships
  platforms <release>     Inspect platform relationships and verification
  config show             Show effective configuration (secrets masked)

Options: --json  machine-readable output | --quiet  suppress human detail
         --verbose  include candidate details | --provider <name>
         --missing  only missing credit rows | --no-cache
`;
function opts(argv: string[]) { const out: any = { _: [] }; for (let i = 0; i < argv.length; i++) { const a = argv[i]; if (a === '--json') out.json = true; else if (a === '--quiet') out.quiet = true; else if (a === '--verbose') out.verbose = true; else if (a === '--missing') out.missing = true; else if (a === '--no-cache') out.noCache = true; else if (a === '--provider') out.provider = argv[++i]; else out._.push(a); } return out; }
function releaseJson(release: Release) { return { ...release, trackCount: release.mediums.reduce((n, m) => n + m.tracks.length, 0), isrcCount: release.mediums.flatMap(m => m.tracks).reduce((n, t) => n + t.isrcs.length, 0) }; }
function print(value: unknown, json: boolean) { if (json) process.stdout.write(JSON.stringify(value, null, 2) + '\n'); else if (typeof value === 'string') process.stdout.write(value + '\n'); else process.stdout.write(JSON.stringify(value, null, 2) + '\n'); }
async function main() {
  const o = opts(process.argv.slice(2)); const [command, input] = o._;
  if (!command || command === '--help' || command === 'help') { print(HELP, false); return; } if (command === '--version' || command === 'version') { print(VERSION, false); return; }
  if (command === 'config' && input === 'show') { print(maskedConfig(await readConfig()), !!o.json); return; }
  if (!input) throw new MbToolError(`Missing release ID or URL. Use --help for usage.`, 2);
  const config = await readConfig(); if (o.noCache) config.cache = false; const http = new HttpClient(config); const mb = new MusicBrainzClient(http); const release = await mb.getRelease(input, o.noCache);
  if (command === 'release') { if (o.json) print(releaseJson(release), true); else { let s = `${release.title} — ${release.artistCredit.map(a => a.name).join(', ') || 'Various Artists'}\nMBID: ${release.id}\n`; if (release.date) s += `Date: ${release.date}${release.country ? ` (${release.country})` : ''}\n`; for (const m of release.mediums) { s += `\nMedium ${m.position}${m.format ? ` (${m.format})` : ''}\n`; for (const t of m.tracks) s += `  ${t.position}. ${t.title}${t.durationMs ? ` [${Math.round(t.durationMs / 60000)}:${String(Math.round(t.durationMs / 1000) % 60).padStart(2, '0')}]` : ''}${t.isrcs.length ? ` — ${t.isrcs.join(', ')}` : ''}\n`; } print(s.trimEnd(), false); } return; }
  if (command === 'isrc') { const rows = await inspectIsrc(release, http, o.provider); if (o.json) print({ release: release.id, rows }, true); else { for (const r of rows) print(`${r.status.padEnd(8)} ${r.track}${r.existing.length ? ` — ${r.existing.join(', ')}` : ''}${o.verbose && r.candidates.length ? `\n          ${r.candidates.map(c => `${c.provider}:${c.isrc || 'no candidate'}`).join(', ')}` : ''}`, false); } return; }
  if (command === 'credits') { const result = await inspectCredits(release, http, o.provider, o.missing); if (o.json) print({ release: release.id, rows: result.rows, diagnostics: result.diagnostics }, true); else { if (result.rows.length) print(result.rows.map(r => `${r.track} | ${r.role} | ${r.person} | ${r.provider} | ${r.confidence.toFixed(2)} | ${r.existingMusicBrainzRelationship ? 'EXISTING' : 'MISSING'} | ${r.sourceUrl}`).join('\n'), false); else print('No external credit rows found.', false); if (result.diagnostics.length && o.verbose) print(result.diagnostics.map(d => `${d.provider}: ${d.status}${d.message ? ` — ${d.message}` : ''}`).join('\n'), false); } return; }
  if (command === 'platforms') { const result = await inspectPlatforms(release, http); if (o.json) print({ release: release.id, platforms: result.platforms, diagnostics: result.diagnostics }, true); else { print(result.platforms.map(r => `${r.status.padEnd(10)} ${r.provider}${r.url ? ` — ${r.url}` : ` — ${r.notes}`}`).join('\n'), false); if (o.verbose && result.diagnostics.length) print(result.diagnostics.map(d => `${d.provider}: ${d.status}${d.message ? ` — ${d.message}` : ''}`).join('\n'), false); } return; }
  if (command === 'inspect') { const tracks = release.mediums.flatMap(m => m.tracks); const isrc = await inspectIsrc(release, http); const credits = await inspectCredits(release, http, undefined, true); const platformResult = await inspectPlatforms(release, http); const externalMissingIsrc = isrc.filter(r => r.status === 'MATCH'); const conflicts = isrc.filter(r => r.status === 'CONFLICT'); const issues = [...(tracks.filter(t => !t.isrcs.length).length ? [`${tracks.filter(t => !t.isrcs.length).length} track(s) without ISRC`] : []), ...(externalMissingIsrc.length ? [`${externalMissingIsrc.length} external ISRC candidate row(s)`] : []), ...(conflicts.length ? [`${conflicts.length} ISRC conflict row(s)`] : []), ...(credits.rows.length ? [`${credits.rows.length} external credit(s) appear missing from MusicBrainz`] : []), ...platformResult.platforms.filter(p => p.status === 'MISSING' || p.status === 'CONFLICT').map(p => `Platform ${p.status.toLowerCase()}: ${p.provider}`)]; const suggestions = [...(externalMissingIsrc.length || conflicts.length ? [`mbtool isrc ${release.id} --verbose`] : []), ...(credits.rows.length ? [`mbtool credits ${release.id} --missing`] : []), ...(platformResult.platforms.some(p => p.status === 'MISSING') ? [`mbtool platforms ${release.id}`] : [])]; const result = { release: releaseJson(release), coverage: { tracks: tracks.length, tracksWithIsrc: tracks.filter(t => t.isrcs.length).length, isrcRows: isrc.length, externalMissingIsrc: externalMissingIsrc.length, isrcConflicts: conflicts.length, existingCredits: tracks.reduce((n, t) => n + t.relationships.length, 0), externalMissingCredits: credits.rows.length }, platforms: platformResult.platforms, diagnostics: [...credits.diagnostics, ...platformResult.diagnostics, ...isrc.flatMap(r => r.diagnostics)], issues, suggestions }; if (o.json) print(result, true); else print(`${release.title}\nTracks: ${result.coverage.tracks}\nISRC coverage: ${result.coverage.tracksWithIsrc}/${result.coverage.tracks}\nExternal missing credits: ${result.coverage.externalMissingCredits}\nIssues:\n${issues.length ? issues.map(i => `- ${i}`).join('\n') : '- none'}${suggestions.length ? `\nSuggestions:\n${suggestions.map(s => `- ${s}`).join('\n')}` : ''}`, false); return; }
  throw new MbToolError(`Unknown command: ${command}. Use --help.`, 2);
}
main().then(() => { if (!process.stdout.writableNeedDrain) process.exit(0); process.stdout.once('drain', () => process.exit(0)); }).catch(error => { const e = error instanceof MbToolError ? error : new MbToolError(error instanceof Error ? error.message : String(error), 1, error); process.stderr.write(`mbtool: ${e.message}\n`); process.exitCode = e.code; });
