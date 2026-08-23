import fs from 'node:fs/promises';
import path from 'node:path';
import { networkError } from '../core/errors.js';
import type { Config } from './config.js';
export class HttpClient {
  private lastMusicBrainz = 0;
  constructor(private readonly config: Config) {}
  async getJson<T>(url: string, options: { cacheKey?: string; noCache?: boolean; headers?: Record<string, string>; rateLimitMs?: number } = {}): Promise<T> {
    const file = options.cacheKey && !options.noCache && this.config.cache ? path.join(this.config.cacheDir, `${options.cacheKey.replace(/[^a-zA-Z0-9._-]/g, '_')}.json`) : undefined;
    if (file) { try { const cached = JSON.parse(await fs.readFile(file, 'utf8')); if (cached.expires > Date.now()) return cached.value as T; } catch {} }
    const delay = options.rateLimitMs ?? 0; if (delay && Date.now() - this.lastMusicBrainz < delay) await new Promise(r => setTimeout(r, delay - (Date.now() - this.lastMusicBrainz)));
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 20_000);
    let response: Response | undefined;
    try { response = await fetch(url, { signal: controller.signal, headers: { Accept: 'application/json', 'User-Agent': this.config.userAgent, ...options.headers } }); this.lastMusicBrainz = Date.now(); } catch (error) { throw networkError(`Network request failed: ${url}`, error); } finally { clearTimeout(timer); }
    if (response.status === 429 || response.status >= 500) { const retry = Number(response.headers.get('retry-after')) || 2; await new Promise(r => setTimeout(r, retry * 1000)); return this.getJson<T>(url, { ...options, noCache: true }); }
    if (!response.ok) throw networkError(`HTTP ${response.status} for ${url}`);
    let value: T; try { value = await response.json() as T; } catch (error) { throw networkError(`Invalid JSON from ${url}`, error); }
    if (file) { await fs.mkdir(this.config.cacheDir, { recursive: true }); await fs.writeFile(file, JSON.stringify({ expires: Date.now() + 86_400_000, value })); }
    return value;
  }
}
