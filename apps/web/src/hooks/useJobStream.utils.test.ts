import { describe, it, expect } from 'vitest';
import {
  applyJobStreamEvent,
  parseJobStreamEventJson,
  mapJobStatus,
  parseLogEntry,
  parseEntityEntry,
  type JobStreamState,
} from './useJobStream.utils';

function createBaseState(): JobStreamState {
  return {
    progress: 0,
    status: 'created',
    logs: [],
    entities: [],
  };
}

describe('applyJobStreamEvent', () => {
  it('updates progress', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, { type: 'progress', data: 42 });
    expect(next.progress).toBe(42);
    expect(next.status).toBe(base.status);
    expect(next.logs).toBe(base.logs);
    expect(next.entities).toBe(base.entities);
  });

  it('ignores non-numeric progress payloads', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, { type: 'progress', data: 'not-a-number' });
    expect(next.progress).toBe(0);
  });

  it('maps known status strings', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, { type: 'status', data: 'EXTRACTING' });
    expect(next.status).toBe('running');
  });

  it('ignores unknown status strings', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, { type: 'status', data: 'UNKNOWN' });
    expect(next.status).toBe('created');
  });

  it('appends log entries', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, {
      type: 'log',
      data: { timestamp: '2026-04-14T12:00:00Z', level: 'INFO', message: 'parsed log' },
    });
    expect(next.logs).toHaveLength(1);
    expect(next.logs[0]).toEqual({
      timestamp: '2026-04-14T12:00:00Z',
      level: 'INFO',
      message: 'parsed log',
    });
  });

  it('falls back to empty log entry when data is malformed', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, { type: 'log', data: { unknown: 'value' } });
    expect(next.logs).toHaveLength(1);
    expect(next.logs[0]).toEqual({
      timestamp: '',
      level: 'INFO',
      message: '',
    });
  });

  it('appends entity entries', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, {
      type: 'entity',
      data: { type: 'capability', name: 'Demand Forecasting' },
    });
    expect(next.entities).toHaveLength(1);
    expect(next.entities[0]).toEqual({
      type: 'capability',
      name: 'Demand Forecasting',
    });
  });

  it('falls back to default entity entry when data is malformed', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, { type: 'entity', data: { unknown: 'value' } });
    expect(next.entities).toHaveLength(1);
    expect(next.entities[0]).toEqual({
      type: 'unknown',
      name: 'Unknown',
    });
  });

  it('leaves state unchanged for complete events', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, { type: 'complete', data: null });
    expect(next).toEqual(base);
  });

  it('leaves state unchanged for error events', () => {
    const base = createBaseState();
    const next = applyJobStreamEvent(base, { type: 'error', data: 'boom' });
    expect(next).toEqual(base);
  });
});

describe('parseJobStreamEventJson', () => {
  it('parses valid extraction job stream events from JSON', () => {
    const event = parseJobStreamEventJson(
      JSON.stringify({
        type: 'progress',
        timestamp: '2026-05-05T21:00:00.000Z',
        data: 45,
      })
    );

    expect(event).toMatchObject({ type: 'progress', data: 45 });
  });

  it('returns null for malformed JSON', () => {
    expect(parseJobStreamEventJson('{not-json')).toBeNull();
  });

  it('returns null for structurally invalid job stream events', () => {
    expect(parseJobStreamEventJson(JSON.stringify({ type: 'unknown', data: 1 }))).toBeNull();
    expect(parseJobStreamEventJson(JSON.stringify({ data: 1 }))).toBeNull();
  });
});

describe('mapJobStatus', () => {
  it('maps backend job statuses to workflow states', () => {
    expect(mapJobStatus('PENDING')).toBe('created');
    expect(mapJobStatus('QUEUED')).toBe('queued');
    expect(mapJobStatus('EXTRACTING')).toBe('running');
    expect(mapJobStatus('COMPLETED')).toBe('succeeded');
    expect(mapJobStatus('FAILED')).toBe('failed_terminal');
    expect(mapJobStatus('CANCELLED')).toBe('cancelled');
    expect(mapJobStatus('PARTIAL_SUCCESS')).toBe('succeeded');
  });

  it('returns created for unknown or empty status strings', () => {
    expect(mapJobStatus('UNKNOWN')).toBe('created');
    expect(mapJobStatus('')).toBe('created');
  });
});

describe('parseLogEntry', () => {
  it('parses a complete log entry', () => {
    const entry = parseLogEntry({ timestamp: 't1', level: 'WARN', message: 'm1' });
    expect(entry).toEqual({ timestamp: 't1', level: 'WARN', message: 'm1' });
  });

  it('returns null for non-record payloads', () => {
    expect(parseLogEntry(null)).toBeNull();
    expect(parseLogEntry('string')).toBeNull();
    expect(parseLogEntry(['array'])).toBeNull();
  });

  it('applies defaults for missing fields', () => {
    const entry = parseLogEntry({});
    expect(entry).toEqual({ timestamp: '', level: 'INFO', message: '' });
  });
});

describe('parseEntityEntry', () => {
  it('parses a complete entity entry', () => {
    const entry = parseEntityEntry({ type: 'capability', name: 'Demand Forecasting' });
    expect(entry).toEqual({ type: 'capability', name: 'Demand Forecasting' });
  });

  it('returns null for non-record payloads', () => {
    expect(parseEntityEntry(null)).toBeNull();
    expect(parseEntityEntry('string')).toBeNull();
    expect(parseEntityEntry(['array'])).toBeNull();
  });

  it('applies defaults for missing fields', () => {
    const entry = parseEntityEntry({});
    expect(entry).toEqual({ type: 'unknown', name: 'Unknown' });
  });
});
