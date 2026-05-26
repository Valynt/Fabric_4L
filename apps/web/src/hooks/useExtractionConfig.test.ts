import { beforeEach, describe, expect, it } from 'vitest';
import { useExtractionConfig } from './useExtractionConfig';

describe('useExtractionConfig', () => {
  beforeEach(() => {
    useExtractionConfig.getState().resetToDefaults();
  });

  it('has expected defaults', () => {
    expect(useExtractionConfig.getState()).toMatchObject({
      sourceUrl: '',
      confidenceThreshold: 0.75,
      chunkSize: 2000,
      chunkOverlap: 200,
      model: 'gpt-4o',
      batchSize: 10,
      priority: 'normal',
    });
  });

  it('clamps invalid numeric payloads and supports partial applyConfig', () => {
    const store = useExtractionConfig.getState();
    store.setConfidenceThreshold(2);
    store.setChunkSize(100);
    store.setChunkOverlap(-10);
    store.setBatchSize(1000);
    store.applyConfig({ sourceUrl: 'https://example.com' });

    const next = useExtractionConfig.getState();
    expect(next.confidenceThreshold).toBe(1);
    expect(next.chunkSize).toBe(500);
    expect(next.chunkOverlap).toBe(0);
    expect(next.batchSize).toBe(100);
    expect(next.sourceUrl).toBe('https://example.com');
  });

  it('builds derived extraction request and defaults entity type for stale all-disabled state', () => {
    const store = useExtractionConfig.getState();
    store.setSourceUrl('https://example.org');
    store.setEntityType('capability', false);
    store.setEntityType('useCase', false);
    store.setEntityType('persona', false);
    store.setEntityType('valueDriver', false);

    expect(store.getExtractionRequest()).toEqual({
      source_url: 'https://example.org',
      extraction_config: {
        entity_types: ['Capability'],
        confidence_threshold: 0.75,
        chunk_size: 2000,
        chunk_overlap: 200,
      },
    });
  });
});
