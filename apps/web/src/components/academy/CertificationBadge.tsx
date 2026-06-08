import { Award } from "lucide-react";
import type { Certification } from "@/hooks/useAcademy";

interface CertificationBadgeProps {
  certification: Certification;
}

export function CertificationBadge({ certification }: CertificationBadgeProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border bg-card p-3">
      <Award className="h-5 w-5 text-amber-500" />
      <div className="min-w-0">
        <p className="text-sm font-medium truncate">{certification.badge_name}</p>
        <p className="text-xs text-muted-foreground">{certification.vos_role}</p>
      </div>
    </div>
  );
}
