import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs/promises';
export interface Config { userAgent: string; discogsToken?: string; cache: boolean; cacheDir: string; }
export function defaultConfig(): Config { return { userAgent: process.env.MBTOOL_USER_AGENT || 'mbtool/0.1.0 (https://github.com/kubrick06010/musicbrainz-userscripts-cli)', discogsToken: process.env.MBTOOL_DISCOGS_TOKEN, cache: true, cacheDir: process.env.XDG_CACHE_HOME ? path.join(process.env.XDG_CACHE_HOME, 'mbtool') : path.join(os.homedir(), '.cache', 'mbtool') }; }
export async function readConfig(): Promise<Config> { const base = defaultConfig(); const file = process.env.XDG_CONFIG_HOME ? path.join(process.env.XDG_CONFIG_HOME, 'mbtool', 'config.json') : path.join(os.homedir(), '.config', 'mbtool', 'config.json'); try { const parsed = JSON.parse(await fs.readFile(file, 'utf8')); return { ...base, ...parsed, userAgent: process.env.MBTOOL_USER_AGENT || parsed.userAgent || base.userAgent, discogsToken: process.env.MBTOOL_DISCOGS_TOKEN || parsed.discogsToken }; } catch { return base; } }
export function maskedConfig(config: Config): Record<string, unknown> { return { ...config, discogsToken: config.discogsToken ? `${config.discogsToken.slice(0, 4)}…${config.discogsToken.slice(-4)}` : undefined }; }
