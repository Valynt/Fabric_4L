/**
 * Dependency Graph Panel - Displays formula dependencies and dependents
 */
import { Skeleton } from "@/components/ui/skeleton";
import { useFormulaDependents, useFormulaDependencies, type DependentAsset } from "@/hooks/useFormulaDependents";

interface DependencyPanelProps {
  formulaId: string;
}

export function DependencyPanel({ formulaId }: DependencyPanelProps) {
  const { data: dependents, isLoading: loadingDeps } = useFormulaDependents(formulaId);
  const { data: dependencies, isLoading: loadingDependencies } = useFormulaDependencies(formulaId);

  if (loadingDeps || loadingDependencies) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
      </div>
    );
  }

  const renderList = (items: DependentAsset[] | undefined, label: string) => (
    <div>
      <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 mb-2">{label}</div>
      {(items || []).length === 0 ? (
        <div className="vf-text-body-s text-muted-foreground py-2">None</div>
      ) : (
        <div className="space-y-1">
          {(items || []).map((item) => (
            <div key={item.id} className="flex items-center gap-2 p-2 bg-secondary/30 rounded-md vf-text-body-s">
              <span className="font-medium truncate">{item.name}</span>
              <span className="ml-auto vf-text-micro text-muted-foreground">{item.type}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      {renderList(dependencies, "This formula depends on")}
      {renderList(dependents, "Used by")}
    </div>
  );
}
