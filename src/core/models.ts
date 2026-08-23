export type MatchConfidence = 'EXACT' | 'HIGH' | 'LIKELY' | 'REVIEW' | 'REJECT';
export type PlatformStatus = 'EXISTING' | 'FOUND' | 'MISSING' | 'CONFLICT' | 'UNVERIFIED';

export interface Artist { id?: string; name: string; sortName?: string; }
export interface ISRC { value: string; source: 'musicbrainz' | 'provider'; }
export interface Credit { trackId?: string; role: string; artist: Artist; provider: string; existingRelationship?: boolean; }
export interface Relationship { type: string; targetType?: string; targetId?: string; targetName?: string; url?: string; attributes?: string[]; }
export interface PlatformLink { provider: string; url: string; status: PlatformStatus; trackCount?: number; notes?: string; }
export interface Track {
  id: string; title: string; number: number; position: string; medium: number; durationMs?: number;
  artists: Artist[]; isrcs: string[]; credits: Credit[]; relationships: Relationship[];
}
export interface Medium { position: number; format?: string; tracks: Track[]; }
export interface Release {
  id: string; title: string; status?: string; date?: string; country?: string; barcode?: string;
  artistCredit: Artist[]; releaseGroupId?: string; releaseGroupTitle?: string; mediums: Medium[];
  relationships: Relationship[]; links: PlatformLink[];
}
export interface ProviderMatch { provider: string; title?: string; artist?: string; url?: string; isrc?: string; trackNumber?: number; durationMs?: number; confidence: number; decision: MatchConfidence; }
export interface MetadataConflict { field: string; values: string[]; tracks?: string[]; }
