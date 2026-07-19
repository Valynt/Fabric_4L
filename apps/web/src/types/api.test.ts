import { describe, expect, it } from 'vitest';

import {
  parseBusinessCaseRoiOutput,
  parseExtractionJob,
  parseIngestionJobs,
  parseWorkflowResult,
} from './api';

describe('parseIngestionJobs', () => {
  it('maps record entries and skips non-record entries in a single pass', () => {
    const jobs = parseIngestionJobs([
      { id: 'job-1', status: 'completed', progress_percent_complete: 100 },
      null,
      'not-a-record',
      42,
      { id: 'job-2', status: 'failed' },
    ]);

    expect(jobs).toEqual([
      {
        id: 'job-1',
        status: 'completed',
        created_at: undefined,
        started_at: undefined,
        updated_at: undefined,
        progress_percent_complete: 100,
        progress_processed_pages: undefined,
        configuration: undefined,
      },
      {
        id: 'job-2',
        status: 'failed',
        created_at: undefined,
        started_at: undefined,
        updated_at: undefined,
        progress_percent_complete: undefined,
        progress_processed_pages: undefined,
        configuration: undefined,
      },
    ]);
  });

  it('returns an empty array for non-array input', () => {
    expect(parseIngestionJobs(undefined)).toEqual([]);
    expect(parseIngestionJobs({ id: 'job-1' })).toEqual([]);
  });
});

describe('parseWorkflowResult', () => {
  it('parses steps while dropping non-record entries', () => {
    const result = parseWorkflowResult({
      output: { company_name: 'Acme' },
      steps: [null, { agent: 'extractor', result: { output: { ok: true } } }],
      completed_at: '2026-01-01T00:00:00Z',
    });

    expect(result.output).toEqual({ company_name: 'Acme' });
    expect(result.steps).toEqual([
      { agent: 'extractor', result: { output: { ok: true } } },
    ]);
    expect(result.completed_at).toBe('2026-01-01T00:00:00Z');
  });
});

describe('parseBusinessCaseRoiOutput', () => {
  it('parses use cases while dropping non-record entries', () => {
    const result = parseBusinessCaseRoiOutput({
      use_cases: [
        'junk',
        { name: 'Reduce churn', roi_value: 120000, confidence: 0.8 },
      ],
      total_value: 120000,
    });

    expect(result.use_cases).toEqual([
      {
        name: 'Reduce churn',
        persona: undefined,
        value_driver: undefined,
        roi_value: 120000,
        payback_months: undefined,
        confidence: 0.8,
      },
    ]);
    expect(result.total_value).toBe(120000);
  });
});

describe('parseExtractionJob', () => {
  it('parses progress logs and extracted entities while dropping non-record entries', () => {
    const result = parseExtractionJob({
      id: 'ext-1',
      progress_logs: [
        { timestamp: '2026-01-01T00:00:00Z', level: 'info', message: 'started' },
        undefined,
      ],
      extracted_entities: [
        null,
        { type: 'Capability', name: 'Route Optimization' },
      ],
    });

    expect(result.progress_logs).toEqual([
      {
        timestamp: '2026-01-01T00:00:00Z',
        level: 'info',
        message: 'started',
        status: undefined,
      },
    ]);
    expect(result.extracted_entities).toEqual([
      { type: 'Capability', name: 'Route Optimization' },
    ]);
  });
});
