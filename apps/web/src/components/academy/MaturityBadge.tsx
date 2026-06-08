import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const LEVEL_COLORS: Record<number, string> = {
  0: "bg-gray-100 text-gray-700",
  1: "bg-blue-100 text-blue-700",
  2: "bg-green-100 text-green-700",
  3: "bg-amber-100 text-amber-700",
  4: "bg-purple-100 text-purple-700",
  5: "bg-rose-100 text-rose-700",
};

interface MaturityBadgeProps {
  level: number;
  name?: string;
  className?: string;
}

export function MaturityBadge({ level, name, className }: MaturityBadgeProps) {
  return (
    <Badge className={cn(LEVEL_COLORS[level] ?? LEVEL_COLORS[0], className)}>
      L{level} {name}
    </Badge>
  );
}
