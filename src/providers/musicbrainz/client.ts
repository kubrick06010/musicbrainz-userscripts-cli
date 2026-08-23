import { invalidInput, musicBrainzError } from '../../core/errors.js';
import { normalizeDuration, normalizeIsrc } from '../../core/normalization.js';
import type { Artist, Credit, Medium, PlatformLink, Relationship, Release, Track } from '../../core/models.js';
import { HttpClient } from '../../shared/http.js';
export function normalizeReleaseInput(input: string): string { const match = input.match(/(?:release|release-group|recording|artist)\/([0-9a-f-]{36})/i); return (match?.[1] || input).toLowerCase(); }
export function isMbid(value: string): boolean { return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value); }
const artists = (credits: any[] = []): Artist[] => credits.map(c => ({ id: c.artist?.id, name: c.name || c.artist?.name || '' })).filter(a => a.name);
const relationships = (rels: any[] = []): Relationship[] => rels.map(r => ({ type: r.type || r['target-type'] || 'relationship', targetType: r['target-type'], targetId: r.artist?.id || r.recording?.id || r.work?.id, targetName: r.artist?.name || r.recording?.title || r.work?.title, url: r.url?.resource, attributes: r.attributes || [] }));
export class MusicBrainzClient {
  constructor(private readonly http: HttpClient) {}
  async getRelease(input: string, noCache = false): Promise<Release> {
    const id = normalizeReleaseInput(input); if (!isMbid(id)) throw invalidInput(`Invalid MusicBrainz release ID or URL: ${input}`);
    const inc = 'artists+artist-credits+labels+recordings+isrcs+release-groups+url-rels+recording-level-rels+artist-rels+work-rels';
    const data: any = await this.http.getJson(`https://musicbrainz.org/ws/2/release/${id}?fmt=json&inc=${inc}`, { cacheKey: `release-${id}`, noCache, rateLimitMs: 1100 });
    if (!data?.id) throw musicBrainzError(`MusicBrainz release not found: ${id}`);
    const links: PlatformLink[] = []; const releaseRels = relationships(data.relations); for (const rel of releaseRels) if (rel.url) { const provider = providerForUrl(rel.url); if (provider) links.push({ provider, url: rel.url, status: 'EXISTING' }); }
    // ISRC Scout and Platform Check deliberately look through the release group because
    // streaming URLs commonly live on a sibling edition while recordings are shared.
    if (data['release-group']?.id) {
      try {
        const group: any = await this.http.getJson(`https://musicbrainz.org/ws/2/release-group/${data['release-group'].id}?fmt=json&inc=url-rels`, { cacheKey: `release-group-${data['release-group'].id}`, noCache, rateLimitMs: 1100 });
        for (const rel of relationships(group.relations)) if (rel.url) { const provider = providerForUrl(rel.url); if (provider && !links.some(l => l.provider === provider && l.url === rel.url)) links.push({ provider, url: rel.url, status: 'FOUND', notes: 'linked on release group' }); }
      } catch { /* a release remains usable when the optional group lookup is unavailable */ }
    }
    const mediums: Medium[] = (data.media || []).map((m: any, mediumIndex: number) => ({ position: m.position || mediumIndex + 1, format: m.format?.name, tracks: (m.tracks || []).map((t: any, trackIndex: number) => { const rec = t.recording || {}; const rels = relationships(rec.relations); const credits = [...artists(rec['artist-credit'] || []), ...rels.filter(r => r.targetType === 'artist' && r.targetName).map(r => ({ id: r.targetId, name: r.targetName! }))].map(a => ({ artist: a, role: 'artist', provider: 'musicbrainz', existingRelationship: true } satisfies Credit)); return { id: rec.id || `track-${mediumIndex + 1}-${trackIndex + 1}`, title: rec.title || t.title || '', number: Number(t.position) || trackIndex + 1, position: String(t.number || t.position || trackIndex + 1), medium: m.position || mediumIndex + 1, durationMs: normalizeDuration(rec.length ?? t.length), artists: artists(rec['artist-credit'] || []), isrcs: (rec.isrcs || []).map(normalizeIsrc).filter(Boolean), credits, relationships: rels } satisfies Track; }) }));
    return { id: data.id, title: data.title || '', status: data.status, date: data.date, country: data.country, barcode: data.barcode, artistCredit: artists(data['artist-credit']), releaseGroupId: data['release-group']?.id, releaseGroupTitle: data['release-group']?.title, mediums, relationships: releaseRels, links };
  }
}
export function providerForUrl(url: string): string | undefined { const host = new URL(url).hostname.toLowerCase(); if (host.includes('spotify')) return 'spotify'; if (host.includes('qobuz')) return 'qobuz'; if (host.includes('tidal')) return 'tidal'; if (host.includes('discogs')) return 'discogs'; if (host.includes('deezer')) return 'deezer'; if (host.includes('bandcamp')) return 'bandcamp'; if (host.includes('apple')) return 'apple'; if (host.includes('soundcloud')) return 'soundcloud'; if (host.includes('beatport')) return 'beatport'; return undefined; }
