/**
 * Canonical API DTOs and defensive parsers.
 *
 * These types describe the shapes produced by runtime parsers, not raw
 * Axios responses.  Where a generated OpenAPI schema is authoritative we
 * derive from it; otherwise we declare the minimal frontend contract.
 */

// =============================================================================
// INGESTION DTOs
// =============================================================================

export type ApiIngestionJobDto = {
  id?: string;
  status?: string;
  created_at?: string;
  started_at?: string;
  updated_at?: string;
  progress_percent_complete?: number;
  progress_processed_pages?: number;
  configuration?: {
    url?: string;
  };
}

export type ApiIngestionAggregationDto = {
  by_status?: Record<string, number>;
  total_records_extracted?: number;
  total_execution_time_ms?: number;
}

// =============================================================================
// WORKFLOW / BUSINESS-CASE DTOs
// =============================================================================

export type ApiWorkflowStepDto = {
  agent?: string;
  result?: {
    output?: unknown;
  };
}

export type ApiBusinessCaseUseCaseDto = {
  name?: string;
  persona?: string;
  value_driver?: string;
  roi_value?: number;
  payback_months?: number;
  confidence?: number;
}

export type ApiBusinessCaseRoiOutputDto = {
  use_cases?: ApiBusinessCaseUseCaseDto[];
  total_value?: number;
  avg_payback_months?: number;
  confidence?: number;
}

export type ApiBusinessCaseNarrativeOutputDto = {
  executive_summary?: string;
}

export type ApiWorkflowResultDto = {
  output?: {
    company_name?: string;
  };
  steps?: ApiWorkflowStepDto[];
  completed_at?: string;
}

// =============================================================================
// EXTRACTION DTOs
// =============================================================================

export type ApiProgressLogDto = {
  timestamp?: string;
  level?: string;
  message?: string;
  status?: string;
}

export type ApiExtractedEntityDto = {
  type?: string;
  name?: string;
}

export type ApiExtractionJobDto = {
  id?: string;
  status?: string;
  progress_percent_complete?: number;
  progress_pages_found?: number;
  progress_processed_pages?: number;
  progress_logs?: ApiProgressLogDto[];
  extracted_entities?: ApiExtractedEntityDto[];
  created_at?: string;
  updated_at?: string;
  configuration?: {
    url?: string;
  };
}

// =============================================================================
// INGESTION JOB DETAIL DTOs
// =============================================================================

export type ApiJobProgressDto = {
  total_pages?: number;
  processed_pages: number;
  failed_pages: number;
  current_url?: string;
  current_stage: string;
  percent_complete: number;
}

export type ApiJobResultsDto = {
  raw_content_count: number;
  extracted_record_count: number;
  storage_bytes_used: number;
  output_location?: string;
}

export type ApiJobResourcesDto = {
  browser_sessions_used: number;
  proxy_requests_made: number;
  llm_tokens_consumed: number;
  compute_time_ms: number;
}

export type ApiJobStageDto = {
  stage: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
}

export type ApiJobErrorDto = {
  id: string;
  stage: string;
  error_code: string;
  error_message: string;
  url?: string;
  retryable: boolean;
  retry_count: number;
  occurred_at: string;
  resolved_at?: string;
}

export type ApiJobDetailDto = {
  id: string;
  target_id: string;
  tenant_id: string;
  configuration: Record<string, unknown>;
  status: string;
  priority: number;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  updated_at?: string;
  estimated_duration_ms?: number;
  progress: ApiJobProgressDto;
  results: ApiJobResultsDto;
  resources: ApiJobResourcesDto;
  triggered_by: string;
  correlation_id?: string;
  created_at: string;
  created_by: string;
  stages: ApiJobStageDto[];
  errors: ApiJobErrorDto[];
}

export type ApiComplianceLogDto = {
  id: string;
  event_type: string;
  severity: string;
  request_url?: string;
  request_timestamp: string;
  response_action_taken?: string;
  created_at: string;
}

// =============================================================================
// DEFENSIVE PARSERS
// =============================================================================

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const asString = (value: unknown): string | undefined =>
  typeof value === 'string' ? value : undefined;

const asNumber = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined;

const asArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

export const parseIngestionJobs = (value: unknown): ApiIngestionJobDto[] =>
  asArray(value).flatMap((item): ApiIngestionJobDto[] =>
    isRecord(item)
      ? [{
          id: asString(item.id),
          status: asString(item.status),
          created_at: asString(item.created_at),
          started_at: asString(item.started_at),
          updated_at: asString(item.updated_at),
          progress_percent_complete: asNumber(item.progress_percent_complete),
          progress_processed_pages: asNumber(item.progress_processed_pages),
          configuration: isRecord(item.configuration) ? { url: asString(item.configuration.url) } : undefined,
        }]
      : [],
  );

export const parseIngestionAggregation = (value: unknown): ApiIngestionAggregationDto => {
  if (!isRecord(value)) return {};
  const byStatusRaw = isRecord(value.by_status) ? value.by_status : undefined;
  const by_status = byStatusRaw
    ? Object.fromEntries(
        Object.entries(byStatusRaw).filter((entry): entry is [string, number] => typeof entry[1] === 'number'),
      )
    : undefined;

  return {
    by_status,
    total_records_extracted: asNumber(value.total_records_extracted),
    total_execution_time_ms: asNumber(value.total_execution_time_ms),
  };
};

export const parseWorkflowResult = (value: unknown): ApiWorkflowResultDto => {
  if (!isRecord(value)) return {};
  const output = isRecord(value.output) ? { company_name: asString(value.output.company_name) } : undefined;
  const steps = asArray(value.steps).flatMap((step): ApiWorkflowStepDto[] =>
    isRecord(step)
      ? [{
          agent: asString(step.agent),
          result: isRecord(step.result) ? { output: step.result.output } : undefined,
        }]
      : [],
  );

  return {
    output,
    steps,
    completed_at: asString(value.completed_at),
  };
};

export const parseBusinessCaseRoiOutput = (value: unknown): ApiBusinessCaseRoiOutputDto => {
  if (!isRecord(value)) return {};
  const use_cases = asArray(value.use_cases).flatMap((useCase): ApiBusinessCaseUseCaseDto[] =>
    isRecord(useCase)
      ? [{
          name: asString(useCase.name),
          persona: asString(useCase.persona),
          value_driver: asString(useCase.value_driver),
          roi_value: asNumber(useCase.roi_value),
          payback_months: asNumber(useCase.payback_months),
          confidence: asNumber(useCase.confidence),
        }]
      : [],
  );
  return {
    use_cases,
    total_value: asNumber(value.total_value),
    avg_payback_months: asNumber(value.avg_payback_months),
    confidence: asNumber(value.confidence),
  };
};

export const parseBusinessCaseNarrativeOutput = (value: unknown): ApiBusinessCaseNarrativeOutputDto =>
  isRecord(value) ? { executive_summary: asString(value.executive_summary) } : {};

export const parseExtractionJob = (value: unknown): ApiExtractionJobDto => {
  if (!isRecord(value)) return {};
  return {
    id: asString(value.id),
    status: asString(value.status),
    progress_percent_complete: asNumber(value.progress_percent_complete),
    progress_pages_found: asNumber(value.progress_pages_found),
    progress_processed_pages: asNumber(value.progress_processed_pages),
    progress_logs: asArray(value.progress_logs).flatMap((log): ApiProgressLogDto[] =>
      isRecord(log)
        ? [{
            timestamp: asString(log.timestamp),
            level: asString(log.level),
            message: asString(log.message),
            status: asString(log.status),
          }]
        : [],
    ),
    extracted_entities: asArray(value.extracted_entities).flatMap((entity): ApiExtractedEntityDto[] =>
      isRecord(entity)
        ? [{
            type: asString(entity.type),
            name: asString(entity.name),
          }]
        : [],
    ),
    created_at: asString(value.created_at),
    updated_at: asString(value.updated_at),
    configuration: isRecord(value.configuration) ? { url: asString(value.configuration.url) } : undefined,
  };
};
