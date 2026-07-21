/**
 * useExtractionConfig.ts - Extraction configuration state management
 * 
 * Provides a Zustand store for managing extraction job configuration
 * with persistence and reset capabilities.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface ExtractionConfig {
  /** Source URL to extract from */
  sourceUrl: string;
  /** Entity types to extract */
  entityTypes: {
    capability: boolean;
    useCase: boolean;
    persona: boolean;
    valueDriver: boolean;
  };
  /** Confidence threshold (0-1) */
  confidenceThreshold: number;
  /** Chunk size for text processing */
  chunkSize: number;
  /** Chunk overlap for text processing */
  chunkOverlap: number;
}

export interface ExtractionControls {
  /** LLM model to use */
  model: 'gpt-4o' | 'gpt-4o-mini' | 'claude-3-sonnet';
  /** Batch size for processing */
  batchSize: number;
  /** Job priority */
  priority: 'low' | 'normal' | 'high';
}

interface ExtractionConfigState extends ExtractionConfig, ExtractionControls {
  // Actions
  setSourceUrl: (url: string) => void;
  setEntityType: (type: keyof ExtractionConfig['entityTypes'], enabled: boolean) => void;
  setConfidenceThreshold: (threshold: number) => void;
  setChunkSize: (size: number) => void;
  setChunkOverlap: (overlap: number) => void;
  setModel: (model: ExtractionControls['model']) => void;
  setBatchSize: (size: number) => void;
  setPriority: (priority: ExtractionControls['priority']) => void;
  applyConfig: (config: Partial<ExtractionConfig>) => void;
  resetToDefaults: () => void;
  getExtractionRequest: () => {
    source_url: string;
    extraction_config: {
      entity_types: string[];
      confidence_threshold: number;
      chunk_size: number;
      chunk_overlap: number;
    };
  };
}

const DEFAULT_CONFIG: ExtractionConfig = {
  sourceUrl: '',
  entityTypes: {
    capability: true,
    useCase: true,
    persona: true,
    valueDriver: true,
  },
  confidenceThreshold: 0.75,
  chunkSize: 2000,
  chunkOverlap: 200,
};

const DEFAULT_CONTROLS: ExtractionControls = {
  model: 'gpt-4o',
  batchSize: 10,
  priority: 'normal',
};

export const useExtractionConfig = create<ExtractionConfigState>()(
  persist(
    (set, get) => ({
      ...DEFAULT_CONFIG,
      ...DEFAULT_CONTROLS,

      setSourceUrl: (url) => set({ sourceUrl: url }),

      setEntityType: (type, enabled) =>
        set((state) => ({
          entityTypes: { ...state.entityTypes, [type]: enabled },
        })),

      setConfidenceThreshold: (threshold) =>
        set({ confidenceThreshold: Math.max(0, Math.min(1, threshold)) }),

      setChunkSize: (size) => set({ chunkSize: Math.max(500, Math.min(8000, size)) }),

      setChunkOverlap: (overlap) => set({ chunkOverlap: Math.max(0, Math.min(500, overlap)) }),

      setModel: (model) => set({ model }),

      setBatchSize: (size) => set({ batchSize: Math.max(1, Math.min(100, size)) }),

      setPriority: (priority) => set({ priority }),

      applyConfig: (config) => set((state) => ({ ...state, ...config })),

      resetToDefaults: () => set({ ...DEFAULT_CONFIG, ...DEFAULT_CONTROLS }),

      getExtractionRequest: () => {
        const state = get();
        const entityTypes = Object.entries(state.entityTypes)
          .flatMap(([, enabled], idx) => {
            if (!enabled) return [];
            const map: Record<string, string> = {
              capability: 'Capability',
              useCase: 'UseCase',
              persona: 'Persona',
              valueDriver: 'ValueDriver',
            };
            const key = Object.keys(state.entityTypes)[idx];
            return map[key] ? [map[key]] : [];
          });

        return {
          source_url: state.sourceUrl,
          extraction_config: {
            entity_types: entityTypes.length > 0 ? entityTypes : ['Capability'],
            confidence_threshold: state.confidenceThreshold,
            chunk_size: state.chunkSize,
            chunk_overlap: state.chunkOverlap,
          },
        };
      },
    }),
    {
      name: 'extraction-config-storage',
      partialize: (state) => ({
        sourceUrl: state.sourceUrl,
        entityTypes: state.entityTypes,
        confidenceThreshold: state.confidenceThreshold,
        chunkSize: state.chunkSize,
        chunkOverlap: state.chunkOverlap,
        model: state.model,
        batchSize: state.batchSize,
        priority: state.priority,
      }),
    }
  )
);
