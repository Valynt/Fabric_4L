import { useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { BookOpen, Trophy, TrendingUp } from "lucide-react";
import ErrorBoundary from "@/components/ErrorBoundary";
import { PageShell } from "@/components/layout/PageShell";
import { PageHeader } from "@/components/ui/fabric/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingState } from "@/components/states/LoadingState";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { PillarCard } from "@/components/academy/PillarCard";
import { ProgressRing } from "@/components/academy/ProgressRing";
import { MaturityBadge } from "@/components/academy/MaturityBadge";
import { CertificationBadge } from "@/components/academy/CertificationBadge";
import {
  usePillars,
  useProgress,
  useCertifications,
  useMaturityLevels,
  useMaturityAssessments,
} from "@/hooks/useAcademy";
import { useAuthContext } from "@/contexts/AuthContext";

function Academy() {
  const navigate = useNavigate();
  const { tenantSlug } = useParams<{ tenantSlug: string }>();
  const { user } = useAuthContext();
  const tenantId = user?.tenantId ?? null;

  const { data: pillarsData, isLoading: pillarsLoading, error: pillarsError } = usePillars(tenantId);
  const { data: progressData, isLoading: progressLoading } = useProgress(tenantId);
  const { data: certsData, isLoading: certsLoading } = useCertifications(tenantId);
  const { data: maturityLevels } = useMaturityLevels(tenantId);
  const { data: assessments } = useMaturityAssessments(tenantId);

  const currentLevel = assessments && assessments.length > 0 ? assessments[0].level : 0;
  const maturityInfo = maturityLevels?.find((m) => m.level === currentLevel);

  const handleLearn = useCallback(
    (pillarId: string) => {
      navigate(`/t/${tenantSlug}/academy/pillars/${pillarId}`);
    },
    [navigate, tenantSlug]
  );

  const handleQuiz = useCallback(
    (pillarId: string) => {
      navigate(`/t/${tenantSlug}/academy/pillars/${pillarId}/quiz`);
    },
    [navigate, tenantSlug]
  );

  const isLoading = pillarsLoading || progressLoading || certsLoading;
  const error = pillarsError;

  if (isLoading) {
    return (
      <PageShell>
        <PageHeader title="Academy" subtitle="Master the Value Operating System" />
        <LoadingState message="Loading academy..." />
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <PageHeader title="Academy" subtitle="Master the Value Operating System" />
        <ErrorState title="Failed to load academy" description={error.message} />
      </PageShell>
    );
  }

  const pillars = pillarsData?.items ?? [];
  const progressMap = new Map(progressData?.items.map((p) => [p.pillar_id, p]));
  const certs = certsData?.items ?? [];
  const overallPct = progressData?.overall_percentage ?? 0;

  return (
    <PageShell>
      <PageHeader
        title="Academy"
        subtitle="Master the Value Operating System through our comprehensive 10-pillar training program"
      />

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        <div className="md:col-span-8 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="h-5 w-5 text-primary" />
                Your VOS Maturity
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-6">
              <ProgressRing percentage={overallPct} size={80} strokeWidth={6} />
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold">L{currentLevel}</span>
                  {maturityInfo && <MaturityBadge level={currentLevel} name={maturityInfo.name} />}
                </div>
                <p className="text-sm text-muted-foreground">{maturityInfo?.description}</p>
                <p className="text-xs text-muted-foreground">
                  {progressData?.completed_count ?? 0} of {progressData?.total_count ?? 10} pillars completed
                </p>
              </div>
            </CardContent>
          </Card>

          <div>
            <h2 className="text-lg font-semibold mb-4">10 VOS Pillars</h2>
            {pillars.length === 0 ? (
              <EmptyState title="No pillars available" description="Check back later for training content." />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {pillars.map((pillar) => (
                  <PillarCard
                    key={pillar.id}
                    pillar={pillar}
                    progress={progressMap.get(pillar.id)}
                    onLearn={handleLearn}
                    onQuiz={handleQuiz}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="md:col-span-4 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Trophy className="h-4 w-4 text-amber-500" />
                Certifications
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {certs.length === 0 ? (
                <p className="text-sm text-muted-foreground">Complete quizzes to earn certifications.</p>
              ) : (
                certs.map((cert) => <CertificationBadge key={cert.id} certification={cert} />)
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Quick Links</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="ghost" className="w-full justify-start" onClick={() => navigate(`/t/${tenantSlug}/academy/resources`)}>
                <BookOpen className="mr-2 h-4 w-4" />
                Resources Library
              </Button>
              <Button variant="ghost" className="w-full justify-start" onClick={() => navigate(`/t/${tenantSlug}/academy/profile`)}>
                <Trophy className="mr-2 h-4 w-4" />
                My Profile
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageShell>
  );
}

export default function AcademyPage() {
  return (
    <ErrorBoundary>
      <Academy />
    </ErrorBoundary>
  );
}
