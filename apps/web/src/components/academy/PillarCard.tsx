import { BookOpen, CheckCircle2, Circle, Clock, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { Pillar, Progress as ProgressItem } from "@/hooks/useAcademy";

interface PillarCardProps {
  pillar: Pillar;
  progress?: ProgressItem;
  onLearn: (pillarId: string) => void;
  onQuiz: (pillarId: string) => void;
}

export function PillarCard({ pillar, progress, onLearn, onQuiz }: PillarCardProps) {
  const status = progress?.status ?? "not_started";
  const pct = progress?.completion_percentage ?? 0;
  const isCompleted = status === "completed";
  const isInProgress = status === "in_progress";

  return (
    <Card className="relative overflow-hidden transition-shadow hover:shadow-md">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
              {pillar.pillar_number}
            </span>
            <CardTitle className="text-base">{pillar.title}</CardTitle>
          </div>
          {isCompleted && <CheckCircle2 className="h-5 w-5 text-green-500" />}
          {isInProgress && <Circle className="h-5 w-5 text-amber-500" />}
        </div>
        <p className="text-sm text-muted-foreground line-clamp-2">{pillar.description}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {pillar.duration && (
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {pillar.duration}
            </span>
          )}
          <span>Target: Level {pillar.target_maturity_level}</span>
        </div>

        {(isInProgress || isCompleted) && (
          <Progress value={pct} className="h-1.5" />
        )}

        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="flex-1" onClick={() => onLearn(pillar.id)}>
            <BookOpen className="mr-1.5 h-3.5 w-3.5" />
            Learn
          </Button>
          <Button size="sm" className="flex-1" onClick={() => onQuiz(pillar.id)} disabled={isCompleted}>
            <Play className="mr-1.5 h-3.5 w-3.5" />
            {isCompleted ? "Completed" : "Take Quiz"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
