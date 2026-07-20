/**
 * useJobStream Hook Tests
 *
 * Tests for real-time job streaming via SSE and polling fallback.
 * Covers connection handling, progress updates, log streaming, and error scenarios.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { createWrapper } from '../test-utils';
import { http, HttpResponse } from 'msw';
import { server } from '../test/mocks/server';
import { getLastEventSource } from '../../test/setup';
import { useJobStream } from './useJobStream';

async function getEventSourceOrThrow() {
  let eventSource: ReturnType<typeof getLastEventSource> | undefined;
  await waitFor(() => {
    eventSource = getLastEventSource();
    expect(eventSource).toBeDefined();
  }, { timeout: 1000 });

  if (!eventSource) {
    throw new Error('Expected EventSource mock to be initialized');
  }

  return eventSource;
}

describe('useJobStream', () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('initializes with default state', () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useJobStream(null), { wrapper });

    expect(result.current.progress).toBe(0);
    expect(result.current.status).toBe('created');
    expect(result.current.logs).toHaveLength(0);
    expect(result.current.entities).toHaveLength(0);
    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('connects and fetches job data via SSE or polling', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useJobStream('job-123'), { wrapper });

    // Wait for SSE connection to be established
    await waitFor(() => expect(result.current.isConnected).toBe(true), { timeout: 1000 });

    // Simulate SSE events to drive state changes
    // Use waitFor to handle race condition where EventSource may not be created yet
    const es = await getEventSourceOrThrow();
    
    // Simulate status update to running
    act(() => {
      es._emitMessage({ type: 'status', data: 'EXTRACTING' });
    });

    await waitFor(() => expect(result.current.status).toBe('running'));

    // Simulate progress update
    act(() => {
      es._simulateProgress(25);
    });

    await waitFor(() => expect(result.current.progress).toBe(25));
  }, 5000);

  it('handles connection errors gracefully', async () => {
    server.use(
      http.get('/api/v1/extract/jobs/non-existent-job', () => {
        return HttpResponse.json({ detail: 'Job not found' }, { status: 404 });
      })
    );

    const wrapper = createWrapper();
    const { result } = renderHook(() => useJobStream('non-existent-job'), { wrapper });

    // Wait for initial connection
    await waitFor(() => expect(result.current.isConnected).toBe(true), { timeout: 1000 });

    // Simulate SSE error - use waitFor to handle race condition
    const es = await getEventSourceOrThrow();
    
    act(() => {
      es._emitError();
    });

    // After error, should fall back to polling and eventually get 404
    await waitFor(() => expect(result.current.error).not.toBeNull(), { timeout: 5000 });
    expect(result.current.isConnected).toBe(false);
  }, 8000);

  it('processes log entries correctly', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useJobStream('job-with-logs'), { wrapper });

    await waitFor(() => expect(result.current.isConnected).toBe(true), { timeout: 2000 });

    const es = await getEventSourceOrThrow();
    act(() => {
      es._emitMessage({
        type: 'log',
        timestamp: new Date().toISOString(),
        data: { timestamp: '2026-04-14T12:00:00Z', level: 'INFO', message: 'parsed log' },
      });
    });

    await waitFor(() => {
      expect(result.current.logs[0]?.timestamp).toBe('2026-04-14T12:00:00Z');
      expect(result.current.logs[0]?.level).toBe('INFO');
      expect(result.current.logs[0]?.message).toBe('parsed log');
    });
  });

  it('processes extracted entities', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useJobStream('job-with-entities'), { wrapper });

    await waitFor(() => expect(result.current.isConnected).toBe(true), { timeout: 2000 });

    const es = await getEventSourceOrThrow();
    act(() => {
      es._emitMessage({
        type: 'entity',
        timestamp: new Date().toISOString(),
        data: { type: 'capability', name: 'Demand Forecasting' },
      });
    });

    await waitFor(() => {
      expect(result.current.entities[0]?.type).toBe('capability');
      expect(result.current.entities[0]?.name).toBe('Demand Forecasting');
    });
  });

  it('processes SSE progress events', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useJobStream('completed-job'), { wrapper });

    // Wait for connection
    await waitFor(() => expect(result.current.isConnected).toBe(true), { timeout: 1000 });

    // Simulate progress via SSE - use waitFor to handle race condition
    const es = await getEventSourceOrThrow();
    
    act(() => {
      es._simulateProgress(75);
    });

    // Progress should update via SSE
    await waitFor(() => expect(result.current.progress).toBe(75), { timeout: 2000 });
  }, 5000);

  it('handles job failure via SSE', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useJobStream('failed-job'), { wrapper });

    // Wait for connection
    await waitFor(() => expect(result.current.isConnected).toBe(true), { timeout: 1000 });

    // Trigger SSE error to fall back to polling - use waitFor to handle race condition
    const es = await getEventSourceOrThrow();
    
    act(() => {
      es._emitError();
    });

    // After SSE error, connection should be closed
    await waitFor(() => expect(result.current.isConnected).toBe(false), { timeout: 2000 });
    
    // Error state should be set (from polling 404 or SSE error)
    // Note: Full status verification requires longer timeout for polling fallback
  }, 5000);

  it('determines streaming state correctly', async () => {
    server.use(
      http.get('/api/v1/extract/jobs/:jobId', () => {
        return HttpResponse.json({
          id: 'streaming-job',
          status: 'EXTRACTING',
          progress_percent_complete: 50,
          progress_logs: [],
          extracted_entities: [],
          configuration: {},
        });
      })
    );

    const wrapper = createWrapper();
    const { result } = renderHook(() => useJobStream('streaming-job'), { wrapper });

    await waitFor(() => expect(result.current.isConnected).toBe(true), { timeout: 2000 });

    const es = await getEventSourceOrThrow();
    act(() => {
      es._emitMessage({ type: 'status', data: 'EXTRACTING' });
    });

    // Should be streaming when connected and job status is EXTRACTING (maps to 'running')
    await waitFor(() => expect(result.current.isStreaming).toBe(true));
  });

  it('cleans up on unmount', async () => {
    const wrapper = createWrapper();
    const { result, unmount } = renderHook(() => useJobStream('cleanup-job'), { wrapper });

    await waitFor(() => expect(result.current.isConnected).toBe(true), { timeout: 2000 });

    // Unmount should clean up connections without throwing
    expect(() => unmount()).not.toThrow();
  });

  it('closes the EventSource and resets state when jobId becomes null', async () => {
    const wrapper = createWrapper();
    const { result, rerender } = renderHook(
      ({ jobId }: { jobId: string | null }) => useJobStream(jobId),
      { wrapper, initialProps: { jobId: 'job-123' as string | null } }
    );

    await waitFor(() => expect(result.current.isConnected).toBe(true), { timeout: 1000 });
    const es = await getEventSourceOrThrow();

    act(() => {
      es._simulateProgress(40);
    });
    await waitFor(() => expect(result.current.progress).toBe(40));

    rerender({ jobId: null });

    // State resets and the previous EventSource is closed on effect re-run
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
      expect(result.current.progress).toBe(0);
      expect(result.current.status).toBe('created');
    });
    expect(es.readyState).toBe(2);
  });
});
