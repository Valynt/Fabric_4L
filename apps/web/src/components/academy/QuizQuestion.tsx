import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import type { QuizQuestion as QuizQuestionType } from "@/hooks/useAcademy";

interface QuizQuestionProps {
  question: QuizQuestionType;
  questionIndex: number;
  selectedAnswer: string | null;
  onSelect: (answer: string) => void;
}

export function QuizQuestionCard({ question, questionIndex, selectedAnswer, onSelect }: QuizQuestionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          <span className="text-muted-foreground mr-2">{questionIndex + 1}.</span>
          {question.question_text}
        </CardTitle>
        <p className="text-xs text-muted-foreground">{question.category} · {question.points} pts</p>
      </CardHeader>
      <CardContent>
        <RadioGroup value={selectedAnswer ?? ""} onValueChange={onSelect}>
          <div className="space-y-2">
            {question.options.map((opt) => (
              <div key={opt.value} className="flex items-center space-x-2 rounded-md border p-3 hover:bg-accent">
                <RadioGroupItem value={opt.value} id={`${question.id}-${opt.value}`} />
                <Label htmlFor={`${question.id}-${opt.value}`} className="flex-1 cursor-pointer">
                  {opt.label}
                </Label>
              </div>
            ))}
          </div>
        </RadioGroup>
      </CardContent>
    </Card>
  );
}
