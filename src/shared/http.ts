import fs from 'node:fs/promises';
import path from 'node:path';
import { networkError } from '../core/errors.js';
import type { Config } from './config.js';
export class HttpClient {
  private lastMusicBrainz = 0;
  constructor(private readonly config: Config) {}
  async getJson<T>(url: string, options: { cacheKey?: string; noCache?: boolean; headers?: Record<string, string>; rateLimitMs?: number; attempt?: number } = {}): Promise<T> {
    const file = options.cacheKey && !options.noCache && this.config.cache ? path.join(this.config.cacheDir, `${options.cacheKey.replace(/[^a-zA-Z0-9._-]/g, '_')}.json`) : undefined;
    if (file) { try { const cached = JSON.parse(await fs.readFile(file, 'utf8')); if (cached.expires > Date.now()) return cached.value as T; } catch {} }
    const delay = options.rateLimitMs ?? 0; if (delay && Date.now() - this.lastMusicBrainz < delay) await new Promise(r => setTimeout(r, delay - (Date.now() - this.lastMusicBrainz)));
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 20_000);
    let response: Response | undefined;
    try { response = await fetch(url, { signal: controller.signal, headers: { Accept: 'application/json', 'User-Agent': this.config.userAgent, ...options.headers } }); this.lastMusicBrainz = Date.now(); } catch (error) { throw networkError(`Network request failed: ${url}`, error); } finally { clearTimeout(timer); }
    if (response.status === 429 || response.status >= 500) { const attempt = options.attempt || 0; if (attempt >= 3) throw networkError(`HTTP ${response.status} after retries for ${url}`); const retry = Math.min(Number(response.headers.get('retry-after')) || 2, 8); await new Promise(r => setTimeout(r, retry * 1000)); return this.getJson<T>(url, { ...options, noCache: true, attempt: attempt + 1 }); }
    if (!response.ok) throw networkError(`HTTP ${response.status} for ${url}`);
    let value: T; try { value = await response.json() as T; } catch (error) { throw networkError(`Invalid JSON from ${url}`, error); }
    if (file) { await fs.mkdir(this.config.cacheDir, { recursive: true }); await fs.writeFile(file, JSON.stringify({ expires: Date.now() + 86_400_000, value })); }
    return value;
  }
  async getText(url: string, options: { headers?: Record<string, string>; rateLimitMs?: number } = {}): Promise<{ status: number; text: string; headers: Headers }> {
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 20_000);
    try {
      if (options.rateLimitMs && Date.now() - this.lastMusicBrainz < options.rateLimitMs) await new Promise(r => setTimeout(r, options.rateLimitMs! - (Date.now() - this.lastMusicBrainz)));
      const response = await fetch(url, { signal: controller.signal, headers: { 'User-Agent': this.config.userAgent, ...options.headers } });
      this.lastMusicBrainz = Date.now(); return { status: response.status, text: await response.text(), headers: response.headers };
    } catch (error) { throw networkError(`Network request failed: ${url}`, error); } finally { clearTimeout(timer); }
  }
  async postForm<T>(url: string, form: Record<string, string>, options: { headers?: Record<string, string> } = {}): Promise<T> {
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 20_000);
    try { const response = await fetch(url, { method: 'POST', signal: controller.signal, headers: { Accept: 'application/json', 'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': this.config.userAgent, ...options.headers }, body: new URLSearchParams(form) }); if (!response.ok) throw networkError(`HTTP ${response.status} for ${url}`); return await response.json() as T; } catch (error) { if (error instanceof Error && error.name === 'MbToolError') throw error; throw networkError(`Network request failed: ${url}`, error); } finally { clearTimeout(timer); }
  }
}
