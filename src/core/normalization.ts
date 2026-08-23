const DIACRITICS = /\p{Diacritic}/gu;
export function normalizeText(value: unknown): string {
  return String(value ?? '').normalize('NFKD').replace(DIACRITICS, '').toLowerCase()
    .replace(/[’'`]/g, '').replace(/&/g, ' and ').replace(/\([^)]*\b(?:mix|edit|version|remaster|remix)\b[^)]*\)/gi, ' ')
    .replace(/[^\p{Letter}\p{Number}]+/gu, ' ').trim().replace(/\s+/g, ' ');
}
export function normalizeArtist(value: string): string { return normalizeText(value).replace(/^(the|a|an) /, ''); }
export function normalizeTitle(value: string): string { return normalizeText(value); }
export function normalizeTrackNumber(value: unknown): number | undefined { const n = Number.parseInt(String(value ?? '').match(/\d+/)?.[0] ?? '', 10); return Number.isFinite(n) ? n : undefined; }
export function normalizeDuration(value: unknown): number | undefined {
  if (value == null || value === '') return undefined;
  const n = Number(value); if (!Number.isFinite(n)) return undefined;
  return n < 1000 ? Math.round(n * 1000) : Math.round(n);
}
export function normalizeIsrc(raw: unknown): string {
  return String(raw ?? '').toUpperCase().replace(/[\s-]/g, '');
}
export function isValidIsrc(value: unknown): boolean { return /^[A-Z]{2}[A-Z0-9]{3}\d{7}$/.test(normalizeIsrc(value)); }
