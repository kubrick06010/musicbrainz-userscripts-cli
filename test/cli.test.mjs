import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
const cli = new URL('../dist/cli/index.js', import.meta.url);
function run(...args) { return spawnSync(process.execPath, [cli.pathname, ...args], { encoding: 'utf8' }); }
test('help and version are executable', () => { const help = run('--help'); assert.equal(help.status, 0); assert.match(help.stdout, /release <release>/); const version = run('--version'); assert.equal(version.status, 0); assert.equal(version.stdout.trim(), '0.1.0'); });
test('invalid MBID has stable usage exit code and stderr', () => { const result = run('inspect', 'invalid'); assert.equal(result.status, 2); assert.match(result.stderr, /Invalid MusicBrainz release/); });
test('config output masks token-shaped values', () => { const result = spawnSync(process.execPath, [cli.pathname, 'config', 'show', '--json'], { encoding: 'utf8', env: { ...process.env, MBTOOL_DISCOGS_TOKEN: 'secret-token-value' } }); assert.equal(result.status, 0); assert.doesNotMatch(result.stdout, /secret-token-value/); });
