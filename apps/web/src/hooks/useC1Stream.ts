/**
 * React hook for Thesys C1 streaming UI
 * Manages partial component renders and streaming state
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { streamC1Response, type C1Message, type C1Component, evaluateWhatIf, saveScenario, getScenarios, isC1Enabled } from '@/api/thesysClient';
import { applyWhatIfResult } from './useC1Stream.utils';

export interface C1StreamState {
  isStreaming: boolean;
  components: C1Component[];
  error: string | null;
  isComplete: boolean;
}

export interface UseC1StreamReturn {
  state: C1StreamState;
  sendQuery: (query: string) => void;
  reset: () => void;
  /** Re-evaluate metrics when slider changes */
  handleSliderChange: (adjustment: { name: string; value: number; original_value: number }) => Promise<void>;
  /** Save current variable state as scenario */
  saveCurrentScenario: (name: string, adjustments: Array<{ name: string; value: number }>) => string;
  /** Get saved scenarios */
  getSavedScenarios: () => ReturnType<typeof getScenarios>;
  /** Check if C1 is available */
  isEnabled: boolean;
}

interface UseC1StreamOptions {
  businessCaseId: string;
  businessCaseData?: Record<string, unknown>;
  onComponentUpdate?: (components: C1Component[]) => void;
}

/**
 * Hook for streaming C1 Generative UI components
 * 
 * Usage:
 * ```tsx
 * const { state, sendQuery, handleSliderChange } = useC1Stream({
 *   businessCaseId: 'bc-123',
 *   businessCaseData: fetchedBusinessCaseData
 * });
 * 
 * // Send a natural language query
 * sendQuery('What if implementation cost doubles?');
 * 
 * // Components stream in via state.components
 * ```
 */
export function useC1Stream(options: UseC1StreamOptions): UseC1StreamReturn {
  const { businessCaseId, businessCaseData, onComponentUpdate } = options;
  const abortControllerRef = useRef<AbortController | null>(null);

  const [state, setState] = useState<C1StreamState>({
    isStreaming: false,
    components: [],
    error: null,
    isComplete: false,
  });

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  /**
   * Send a natural language query to C1
   */
  const sendQuery = useCallback((query: string) => {
    // Cancel any existing stream and clear ref to prevent race conditions
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    abortControllerRef.current = new AbortController();

    setState({
      isStreaming: true,
      components: [],
      error: null,
      isComplete: false,
    });

    const messages: C1Message[] = [
      {
        role: 'system',
        content: `You are an interactive business case explorer. The user is analyzing business case ${businessCaseId}. 
Generate UI components (sliders, metric cards, scenario buttons) that let them explore "what-if" scenarios.
Available components: Slider, MetricCard, SaveScenarioButton, ScenarioSelector.
When sliders change, the system will recalculate metrics via the formula API.`,
      },
      {
        role: 'user',
        content: query,
      },
    ];

    // Start streaming
    (async () => {
      try {
        const stream = streamC1Response(
          messages,
          businessCaseId,
          businessCaseData,
          abortControllerRef.current?.signal
        );

        for await (const chunk of stream) {
          if (abortControllerRef.current?.signal.aborted) {
            break;
          }

          switch (chunk.type) {
            case 'component':
              if (chunk.data && typeof chunk.data === 'object') {
                const component = chunk.data as C1Component;
                setState(prev => {
                  const updated = [...prev.components, component];
                  onComponentUpdate?.(updated);
                  return { ...prev, components: updated };
                });
              }
              break;

            case 'error':
              setState(prev => ({
                ...prev,
                error: chunk.error || 'Unknown streaming error',
                isStreaming: false,
              }));
              break;

            case 'done':
              setState(prev => ({
                ...prev,
                isStreaming: false,
                isComplete: true,
              }));
              // Clean up AbortController when stream completes naturally
              if (abortControllerRef.current) {
                abortControllerRef.current = null;
              }
              break;
          }
        }
      } catch (error) {
        setState(prev => ({
          ...prev,
          error: error instanceof Error ? error.message : 'Stream failed',
          isStreaming: false,
        }));
      }
    })();
  }, [businessCaseId, businessCaseData, onComponentUpdate]);

  /**
   * Handle slider value changes - recalculate via Formula API
   */
  const handleSliderChange = useCallback(async (adjustment: { name: string; value: number; original_value: number }) => {
    try {
      const result = await evaluateWhatIf(businessCaseId, [adjustment], businessCaseData);

      // Update components with new values based on label patterns
      setState(prev => ({
        ...prev,
        components: applyWhatIfResult(prev.components, result),
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to recalculate',
        isStreaming: false,
      }));
    }
  }, [businessCaseId]);

  /**
   * Save current scenario to localStorage
   */
  const saveCurrentScenario = useCallback((name: string, adjustments: Array<{ name: string; value: number }>) => {
    return saveScenario(businessCaseId, name, adjustments);
  }, [businessCaseId]);

  /**
   * Get saved scenarios for this business case
   */
  const getSavedScenarios = useCallback(() => {
    return getScenarios(businessCaseId);
  }, [businessCaseId]);

  /**
   * Reset the stream state
   */
  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setState({
      isStreaming: false,
      components: [],
      error: null,
      isComplete: false,
    });
  }, []);

  // Check if C1 is enabled at runtime
  const isEnabled = isC1Enabled();

  return {
    state,
    sendQuery,
    reset,
    handleSliderChange,
    saveCurrentScenario,
    getSavedScenarios,
    isEnabled,
  };
}

export default useC1Stream;
