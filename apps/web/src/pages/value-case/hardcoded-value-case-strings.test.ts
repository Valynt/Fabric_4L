import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const pagePath = path.resolve(__dirname, 'ValueCasePage.tsx');
const source = fs.readFileSync(pagePath, 'utf-8');

const LEGACY_HARDCODED_STRINGS = [
  'Economic buyer',
  'Business champion',
  'Technical evaluator',
  'Validated calculator assumptions',
  'Accepted business pains from discovery',
  'Conservative ramp in Q1',
  'Expected adoption by Q2',
  '$1.8M',
  '214%',
  '9 months',
  'Change management capacity',
  'Competing budget priorities',
];

describe('ValueCasePage hardcoded input regression guard', () => {
  it.each(LEGACY_HARDCODED_STRINGS)('does not contain %s', (legacyString) => {
    expect(source).not.toContain(legacyString);
  });
});
