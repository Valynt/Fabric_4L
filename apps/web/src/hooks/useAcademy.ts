import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/api/typedClient";
import { withApiError, STALE_TIME, RETRY_CONFIG } from "@/hooks/useApiShared";
import { QK } from "@/hooks/queryKeys";

// --- Types ---

export interface Pillar {
  id: string;
  pillar_number: number;
  title: string;
  description: string;
  target_maturity_level: number;
  duration: string | null;
  content: {
    overview: string;
    learning_objectives: string[];
    key_takeaways: string[];
    resources: Array<{ title: string; url: string; type: string }>;
  } | null;
}

export interface PillarListResponse {
  items: Pillar[];
  total: number;
}

export interface QuizQuestion {
  id: string;
  question_number: number;
  question_type: string;
  category: string;
  question_text: string;
  options: Array<{ label: string; value: string }>;
  points: number;
}

export interface QuizListResponse {
  items: QuizQuestion[];
  total: number;
}

export interface QuizAnswer {
  question_id: string;
  selected_answer: string;
}

export interface QuizResult {
  id: string;
  score: number;
  passed: boolean;
  feedback: {
    overall: string;
    strengths: string[];
    improvements: string[];
    next_steps: string[];
  };
  attempt_number: number;
}

export interface Progress {
  id: string;
  pillar_id: string;
  status: "not_started" | "in_progress" | "completed";
  completion_percentage: number;
}

export interface ProgressListResponse {
  items: Progress[];
  overall_percentage: number;
  completed_count: number;
  total_count: number;
}

export interface Certification {
  id: string;
  badge_name: string;
  pillar_id: string;
  vos_role: string;
  awarded_at: string;
}

export interface MaturityLevel {
  level: number;
  name: string;
  description: string;
  behaviors: string[];
}

export interface MaturityAssessment {
  id: string;
  level: number;
  assessment_data: {
    self_assessment: number;
    quiz_average: number;
    pillars_completed: number;
    behavior_indicators: string[];
    recommendations: string[];
  };
  assessed_at: string;
}

export interface AcademyResource {
  id: string;
  title: string;
  description: string | null;
  resource_type: string;
  file_url: string;
}

class AcademyApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AcademyApiError";
  }
}

// --- Fetchers ---

async function fetchPillars(): Promise<PillarListResponse> {
  const res = await apiGet<PillarListResponse>("l5", "/academy/pillars");
  return res.data;
}

async function fetchQuiz(pillarId: string): Promise<QuizListResponse> {
  const res = await apiGet<QuizListResponse>("l5", `/academy/pillars/${pillarId}/quiz`);
  return res.data;
}

async function submitQuizPayload(pillarId: string, answers: QuizAnswer[]): Promise<QuizResult> {
  const res = await apiPost<QuizResult>("l5", "/academy/quiz/submit", {
    pillar_id: pillarId,
    answers,
  });
  return res.data;
}

async function fetchProgress(): Promise<ProgressListResponse> {
  const res = await apiGet<ProgressListResponse>("l5", "/academy/progress");
  return res.data;
}

async function updateProgressPayload(pillarId: string, status: string, completionPercentage: number): Promise<Progress> {
  const res = await apiPut<Progress>("l5", "/academy/progress", {
    pillar_id: pillarId,
    status,
    completion_percentage: completionPercentage,
  });
  return res.data;
}

async function fetchCertifications(): Promise<{ items: Certification[]; total: number }> {
  const res = await apiGet<{ items: Certification[]; total: number }>("l5", "/academy/certifications");
  return res.data;
}

async function fetchMaturityLevels(): Promise<MaturityLevel[]> {
  const res = await apiGet<MaturityLevel[]>("l5", "/academy/maturity/levels");
  return res.data;
}

async function fetchMaturityAssessments(): Promise<MaturityAssessment[]> {
  const res = await apiGet<MaturityAssessment[]>("l5", "/academy/maturity/assessments");
  return res.data;
}

async function createMaturityAssessmentPayload(level: number, assessmentData: MaturityAssessment["assessment_data"]): Promise<MaturityAssessment> {
  const res = await apiPost<MaturityAssessment>("l5", "/academy/maturity/assessments", {
    level,
    assessment_data: assessmentData,
  });
  return res.data;
}

async function fetchResources(): Promise<{ items: AcademyResource[]; total: number }> {
  const res = await apiGet<{ items: AcademyResource[]; total: number }>("l5", "/academy/resources");
  return res.data;
}

// --- Hooks ---

export function usePillars(tenantId: string | null) {
  return useQuery<PillarListResponse, AcademyApiError>({
    queryKey: tenantId ? QK.academy.pillars(tenantId) : ["academy", "pillars"],
    queryFn: () => withApiError(fetchPillars(), AcademyApiError),
    enabled: !!tenantId,
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useQuiz(tenantId: string | null, pillarId: string | null) {
  return useQuery<QuizListResponse, AcademyApiError>({
    queryKey: tenantId && pillarId ? QK.academy.quiz(tenantId, pillarId) : ["academy", "quiz"],
    queryFn: async () => {
      if (!pillarId) throw new AcademyApiError("Missing pillarId");
      return withApiError(fetchQuiz(pillarId), AcademyApiError);
    },
    enabled: !!tenantId && !!pillarId,
    staleTime: STALE_TIME.detail,
  });
}

export function useSubmitQuiz(tenantId: string | null) {
  const queryClient = useQueryClient();
  return useMutation<QuizResult, AcademyApiError, { pillarId: string; answers: QuizAnswer[] }>({
    mutationFn: ({ pillarId, answers }) => withApiError(submitQuizPayload(pillarId, answers), AcademyApiError),
    onSuccess: (_, vars) => {
      if (tenantId) {
        queryClient.invalidateQueries({ queryKey: QK.academy.progress(tenantId) });
        queryClient.invalidateQueries({ queryKey: QK.academy.certifications(tenantId) });
        queryClient.invalidateQueries({ queryKey: QK.academy.quiz(tenantId, vars.pillarId) });
      }
    },
  });
}

export function useProgress(tenantId: string | null) {
  return useQuery<ProgressListResponse, AcademyApiError>({
    queryKey: tenantId ? QK.academy.progress(tenantId) : ["academy", "progress"],
    queryFn: () => withApiError(fetchProgress(), AcademyApiError),
    enabled: !!tenantId,
    staleTime: STALE_TIME.list,
  });
}

export function useUpdateProgress(tenantId: string | null) {
  const queryClient = useQueryClient();
  return useMutation<Progress, AcademyApiError, { pillarId: string; status: string; completionPercentage: number }>({
    mutationFn: ({ pillarId, status, completionPercentage }) =>
      withApiError(updateProgressPayload(pillarId, status, completionPercentage), AcademyApiError),
    onSuccess: () => {
      if (tenantId) {
        queryClient.invalidateQueries({ queryKey: QK.academy.progress(tenantId) });
      }
    },
  });
}

export function useCertifications(tenantId: string | null) {
  return useQuery<{ items: Certification[]; total: number }, AcademyApiError>({
    queryKey: tenantId ? QK.academy.certifications(tenantId) : ["academy", "certifications"],
    queryFn: () => withApiError(fetchCertifications(), AcademyApiError),
    enabled: !!tenantId,
    staleTime: STALE_TIME.list,
  });
}

export function useMaturityLevels(tenantId: string | null) {
  return useQuery<MaturityLevel[], AcademyApiError>({
    queryKey: tenantId ? QK.academy.maturityLevels(tenantId) : ["academy", "maturity-levels"],
    queryFn: () => withApiError(fetchMaturityLevels(), AcademyApiError),
    enabled: !!tenantId,
    staleTime: STALE_TIME.list,
  });
}

export function useMaturityAssessments(tenantId: string | null) {
  return useQuery<MaturityAssessment[], AcademyApiError>({
    queryKey: tenantId ? QK.academy.maturityAssessments(tenantId) : ["academy", "maturity-assessments"],
    queryFn: () => withApiError(fetchMaturityAssessments(), AcademyApiError),
    enabled: !!tenantId,
    staleTime: STALE_TIME.list,
  });
}

export function useCreateMaturityAssessment(tenantId: string | null) {
  const queryClient = useQueryClient();
  return useMutation<MaturityAssessment, AcademyApiError, { level: number; assessmentData: MaturityAssessment["assessment_data"] }>({
    mutationFn: ({ level, assessmentData }) =>
      withApiError(createMaturityAssessmentPayload(level, assessmentData), AcademyApiError),
    onSuccess: () => {
      if (tenantId) {
        queryClient.invalidateQueries({ queryKey: QK.academy.maturityAssessments(tenantId) });
      }
    },
  });
}

export function useResources(tenantId: string | null) {
  return useQuery<{ items: AcademyResource[]; total: number }, AcademyApiError>({
    queryKey: tenantId ? QK.academy.resources(tenantId) : ["academy", "resources"],
    queryFn: () => withApiError(fetchResources(), AcademyApiError),
    enabled: !!tenantId,
    staleTime: STALE_TIME.list,
  });
}
