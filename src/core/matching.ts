import { normalizeArtist, normalizeDuration, normalizeTitle } from './normalization.js';
import type { ProviderMatch, Track } from './models.js';
export function scoreCandidate(track: Track, candidate: ProviderMatch): number {
  let score = 0; let weight = 0;
  if (candidate.title) { weight += 0.45; if (normalizeTitle(track.title) === normalizeTitle(candidate.title)) score += 0.45; else if (normalizeTitle(track.title).includes(normalizeTitle(candidate.title)) || normalizeTitle(candidate.title).includes(normalizeTitle(track.title))) score += 0.25; }
  if (candidate.artist) { weight += 0.25; const expected = track.artists.map(a => normalizeArtist(a.name)); if (expected.some(a => a === normalizeArtist(candidate.artist!))) score += 0.25; }
  if (candidate.trackNumber != null) { weight += 0.15; if (candidate.trackNumber === track.number) score += 0.15; }
  const d = normalizeDuration(candidate.durationMs); if (d != null && track.durationMs != null) { weight += 0.15; if (Math.abs(d - track.durationMs) <= 3000) score += 0.15; else if (Math.abs(d - track.durationMs) <= 10000) score += 0.07; }
  return weight ? Math.min(1, score / weight) : 0;
}
export function classifyConfidence(score: number): ProviderMatch['decision'] { return score >= .95 ? 'EXACT' : score >= .8 ? 'HIGH' : score >= .6 ? 'LIKELY' : score >= .4 ? 'REVIEW' : 'REJECT'; }
export function compareTrack(track: Track, candidate: ProviderMatch): ProviderMatch { const confidence = scoreCandidate(track, candidate); return { ...candidate, confidence, decision: classifyConfidence(confidence) }; }
