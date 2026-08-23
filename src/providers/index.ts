import type { ProviderMatch, Release } from '../core/models.js';
import { compareTrack } from '../core/matching.js';
import { normalizeIsrc } from '../core/normalization.js';
import { HttpClient } from '../shared/http.js';

export const PROVIDERS = ['discogs', 'qobuz', 'tidal', 'deezer', 'spotify', 'bandcamp', 'apple', 'beatport', 'soundcloud'];
export interface IsrcRow { track: string; existing: string[]; status: 'EXISTING' | 'MISSING' | 'MATCH' | 'CONFLICT'; candidates: ProviderMatch[]; }
export interface CreditRow { track: string; role: string; person: string; provider: string; existingMusicBrainzRelationship: boolean; candidate: string; confidence: number; }

function providerOf(url: string): string | undefined { try { const h = new URL(url).hostname; return PROVIDERS.find(p => h.includes(p)); } catch { return undefined; } }
function providerLinks(release: Release, selected?: string): Array<{ provider: string; url: string }> { return release.links.filter(l => !selected || l.provider === selected).map(l => ({ provider: l.provider, url: l.url })); }
export async function inspectIsrc(release: Release, http: HttpClient, selected?: string): Promise<IsrcRow[]> {
  const links = providerLinks(release, selected); const rows: IsrcRow[] = [];
  for (const track of release.mediums.flatMap(m => m.tracks)) {
    const existing = track.isrcs.map(normalizeIsrc).filter(Boolean); const candidates: ProviderMatch[] = [];
    for (const link of links) { candidates.push({ provider: link.provider, url: link.url, title: track.title, isrc: undefined, confidence: 0, decision: 'REVIEW' }); }
    // Deezer's public API is a safe, unauthenticated discovery source when an album link is present.
    const deezer = links.find(l => l.provider === 'deezer');
    if (deezer) { const id = deezer.url.match(/album\/(\d+)/i)?.[1]; if (id) { try { const data: any = await http.getJson(`https://api.deezer.com/album/${id}`, { cacheKey: `deezer-${id}` }); const hit = (data.tracks?.data || []).find((t: any) => t.track_position === track.number || t.title?.toLowerCase() === track.title.toLowerCase()); if (hit?.isrc) candidates.push({ provider: 'deezer', url: hit.link, title: hit.title, artist: hit.artist?.name, trackNumber: hit.track_position, durationMs: Number(hit.duration) * 1000, isrc: normalizeIsrc(hit.isrc), confidence: 1, decision: 'EXACT' }); } catch { /* provider absence is represented as no candidate */ } } }
    const values = [...new Set(candidates.map(c => c.isrc).filter(Boolean))]; const conflict = values.length > 1; const status = existing.length ? (conflict ? 'CONFLICT' : 'EXISTING') : (values.length ? 'MATCH' : 'MISSING'); rows.push({ track: track.title, existing, status, candidates });
  }
  return rows;
}
export function inspectCredits(release: Release, selected?: string, missingOnly = false): CreditRow[] {
  const rows: CreditRow[] = [];
  for (const track of release.mediums.flatMap(m => m.tracks)) for (const rel of track.relationships.filter(r => r.targetType === 'artist' && r.targetName)) { const provider = rel.url ? providerOf(rel.url) || 'musicbrainz' : 'musicbrainz'; if (selected && provider !== selected) continue; const row = { track: track.title, role: rel.type, person: rel.targetName!, provider, existingMusicBrainzRelationship: true, candidate: rel.targetName!, confidence: 1 }; if (!missingOnly) rows.push(row); }
  for (const rel of release.relationships.filter(r => r.targetType === 'artist' && r.targetName)) { const provider = rel.url ? providerOf(rel.url) || 'musicbrainz' : 'musicbrainz'; if (selected && provider !== selected) continue; if (!missingOnly) rows.push({ track: '[release]', role: rel.type, person: rel.targetName!, provider, existingMusicBrainzRelationship: true, candidate: rel.targetName!, confidence: 1 }); }
  if (missingOnly && !rows.length) return [];
  return rows;
}
export async function inspectPlatforms(release: Release, http: HttpClient): Promise<Release['links']> {
  const byProvider = new Map(release.links.map(link => [link.provider, link]));
  for (const provider of PROVIDERS) if (!byProvider.has(provider)) byProvider.set(provider, { provider, url: '', status: 'UNVERIFIED', notes: 'No MusicBrainz relationship; provider search not configured for this release.' });
  return [...byProvider.values()];
}
