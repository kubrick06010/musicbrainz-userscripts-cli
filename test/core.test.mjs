import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeText, normalizeIsrc, isValidIsrc, normalizeDuration } from '../dist/core/normalization.js';
import { classifyConfidence } from '../dist/core/matching.js';

test('normalization handles Unicode and punctuation', () => {
  assert.equal(normalizeText('Beyoncé — Déjà Vu!'), 'beyonce deja vu');
  assert.equal(normalizeText('Artist (Radio Edit)'), 'artist');
});
test('ISRC normalization and validation follow upstream format', () => {
  assert.equal(normalizeIsrc('us-abc-12-34567'), 'USABC1234567');
  assert.equal(isValidIsrc('USABC1234567'), true);
  assert.equal(isValidIsrc('bad-value'), false);
});
test('duration normalization accepts seconds and milliseconds', () => {
  assert.equal(normalizeDuration(215), 215000);
  assert.equal(normalizeDuration(215000), 215000);
  assert.equal(normalizeDuration(undefined), undefined);
});
test('confidence thresholds are deterministic', () => {
  assert.equal(classifyConfidence(1), 'EXACT');
  assert.equal(classifyConfidence(.85), 'HIGH');
  assert.equal(classifyConfidence(.65), 'LIKELY');
  assert.equal(classifyConfidence(.45), 'REVIEW');
  assert.equal(classifyConfidence(.2), 'REJECT');
});
