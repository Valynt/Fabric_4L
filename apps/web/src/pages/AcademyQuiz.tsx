import { useCallback, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useNavigation } from "@/hooks/useNavigation";
import { ArrowLeft, CheckCircle2, XCircle, RotateCcw, Trophy } from "lucide-react";
import ErrorBoundary from "@/components/ErrorBoundary";
import { PageShell } from "@/components/layout/PageShell";
import { PageHeader } from "@/components/ui/fabric/PageHeader";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { LoadingState } from "@/components/states/LoadingState";
import { ErrorState } from "@/components/states/ErrorState";
import { QuizQuestionCard } from "@/components/academy/QuizQuestion";
import { useQuiz, useSubmitQuiz, type QuizAnswer } from "@/hooks/useAcademy";
import { useAuthContext } from "@/contexts/AuthContext";

function AcademyQuiz() {
  const { navigateTo } = useNavigation();
  const { tenantSlug, pillarId } = useParams<{ tenantSlug: string; pillarId: string }>();
  const { user } = useAuthContext();
  const tenantId = user?.tenantId ?? null;

  const { data: quizData, isLoading, error } = useQuiz(tenantId, pillarId ?? null);
  const submitQuiz = useSubmitQuiz(tenantId);

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<Awaited<ReturnType<typeof submitQuiz.mutateAsync>> | null>(null);

  const questions = useMemo(() => quizData?.items ?? [], [quizData]);

  const handleSelect = useCallback((questionId: string, answer: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: answer }));
  }, []);

  const allAnswered = useMemo(() => {
    return questions.length > 0 && questions.every((q) => answers[q.id]);
  }, [questions, answers]);

  const handleSubmit = useCallback(async () => {
    if (!pillarId || !allAnswered) return;
    const answerList: QuizAnswer[] = questions.map((q) => ({
      question_id: q.id,
      selected_answer: answers[q.id],
    }));
    const res = await submitQuiz.mutateAsync({ pillarId, answers: answerList });
    setResult(res);
    setSubmitted(true);
  }, [pillarId, allAnswered, questions, answers, submitQuiz]);

  const handleRetry = useCallback(() => {
    setAnswers({});
    setSubmitted(false);
    setResult(null);
  }, []);

  if (isLoading) {
    return (
      <PageShell>
        <LoadingState message="Loading quiz..." />
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState title="Failed to load quiz" description={error.message} />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        title="Quiz"
        subtitle={`${questions.length} questions · Pillar ${pillarId}`}
        actions={
          <Button variant="ghost" size="sm" onClick={() => navigateTo("academy", { tenantSlug })}>
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            Back to Academy
          </Button>
        }
      />

      <div className="max-w-2xl mx-auto space-y-6">
        {submitted && result && (
          <Alert className={result.passed ? "border-green-500 bg-green-50" : "border-red-500 bg-red-50"}>
            {result.passed ? (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            ) : (
              <XCircle className="h-5 w-5 text-red-600" />
            )}
            <AlertTitle className={result.passed ? "text-green-800" : "text-red-800"}>
              {result.passed ? `Passed! Score: ${result.score}%` : `Did not pass. Score: ${result.score}%`}
            </AlertTitle>
            <AlertDescription className="space-y-2">
              <p>{result.feedback.overall}</p>
              {result.feedback.strengths.length > 0 && (
                <ul className="text-sm list-disc pl-4">
                  {result.feedback.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              )}
              {result.passed && (
                <div className="flex items-center gap-2 text-amber-700">
                  <Trophy className="h-4 w-4" />
                  <span className="text-sm font-medium">Certification awarded!</span>
                </div>
              )}
            </AlertDescription>
            <div className="mt-3">
              <Button variant="outline" size="sm" onClick={handleRetry}>
                <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                Retake Quiz
              </Button>
            </div>
          </Alert>
        )}

        {!submitted &&
          questions.map((q, idx) => (
            <QuizQuestionCard
              key={q.id}
              question={q}
              questionIndex={idx}
              selectedAnswer={answers[q.id] ?? null}
              onSelect={(ans) => handleSelect(q.id, ans)}
            />
          ))}

        {!submitted && questions.length > 0 && (
          <div className="flex justify-end">
            <Button onClick={handleSubmit} disabled={!allAnswered || submitQuiz.isPending}>
              {submitQuiz.isPending ? "Submitting..." : "Submit Quiz"}
            </Button>
          </div>
        )}
      </div>
    </PageShell>
  );
}

export default function AcademyQuizPage() {
  return (
    <ErrorBoundary>
      <AcademyQuiz />
    </ErrorBoundary>
  );
}
