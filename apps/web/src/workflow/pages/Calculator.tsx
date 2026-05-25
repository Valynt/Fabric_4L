import { useCallback } from "react";
import { useNavigation } from "@/hooks/useNavigation";
import { WorkflowLayout } from "../components/WorkflowLayout";
import { useWorkflowStore } from "../store/workflowStore";
import { STEPS } from "../constants";
import { ValueLeversCalculator } from "@/components/calculator/ValueLeversCalculator";

export default function Calculator() {
  const { navigateTo } = useNavigation();
  const { setCurrentStep, setGeneratedCaseId, prospect } = useWorkflowStore();

  const companySize = prospect?.employees ? (prospect.employees > 5000 ? "Enterprise" : "SMB") : undefined;

  const handleSaved = useCallback((valueCase: { case_id: string }) => {
    setGeneratedCaseId(valueCase.case_id);
    setCurrentStep(STEPS.VALUE_CASE);
    navigateTo('/workflow/value-case');
  }, [navigateTo, setCurrentStep, setGeneratedCaseId]);

  return (
    <WorkflowLayout>
      <main className="w-full space-y-4" aria-label="Value Calculator">
        <header><h1 className="text-xl font-bold text-foreground">Value Calculator</h1></header>
        <ValueLeversCalculator
          accountId={prospect?.companyId ?? ""}
          industry={prospect?.industry}
          companySize={companySize}
          onSaved={handleSaved}
        />
      </main>
    </WorkflowLayout>
  );
}
