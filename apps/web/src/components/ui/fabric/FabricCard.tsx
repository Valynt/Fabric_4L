import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface FabricCardProps {
  children: React.ReactNode;
  className?: string;
  padding?: "none" | "compact" | "normal" | "loose";
  shadow?: "none" | "sm" | "md" | "lg";
  title?: string;
  description?: string;
  headerActions?: React.ReactNode;
}

const paddingMap = {
  none: "",
  compact: "p-4",
  normal: "p-6",
  loose: "p-8",
};

const shadowMap = {
  none: "",
  sm: "shadow-sm",
  md: "shadow-md",
  lg: "shadow-lg",
};

export function FabricCard({
  children,
  className,
  padding = "normal",
  shadow = "sm",
  title,
  description,
  headerActions,
}: FabricCardProps) {
  return (
    <Card className={cn("border-border", shadowMap[shadow], className)}>
      {(title || description || headerActions) && (
        <CardHeader className={cn("flex flex-row items-start justify-between", padding !== "none" && paddingMap[padding])}>
          <div className="flex-1 min-w-0">
            {title && <CardTitle className="text-base font-semibold">{title}</CardTitle>}
            {description && (
              <CardDescription className="vf-text-body-m mt-1">{description}</CardDescription>
            )}
          </div>
          {headerActions && <div className="flex items-center gap-2 flex-shrink-0">{headerActions}</div>}
        </CardHeader>
      )}
      <CardContent className={cn(padding !== "none" && !title && !description && paddingMap[padding])}>
        {children}
      </CardContent>
    </Card>
  );
}
