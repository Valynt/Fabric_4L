import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { OptimizedImage } from "@/components/ui/optimized-image";
import { StatusBadge } from "./StatusBadge";
import { cn } from "@/lib/utils";

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar?: string;
}

export interface TeamMemberListProps {
  members: TeamMember[];
  className?: string;
  onMemberClick?: (member: TeamMember) => void;
  actions?: (member: TeamMember) => React.ReactNode;
}

export function TeamMemberList({ members, className, onMemberClick, actions }: TeamMemberListProps) {
  return (
    <div className={cn("divide-y divide-border", className)}>
      {members.map((member) => (
        <div
          key={member.id}
          onClick={() => onMemberClick?.(member)}
          className={cn(
            "flex items-center gap-4 py-3 px-4",
            onMemberClick && "cursor-pointer hover:bg-muted/30 transition-colors"
          )}
        >
          <Avatar className="h-8 w-8 bg-muted">
            {member.avatar ? (
              <OptimizedImage src={member.avatar} alt={member.name} />
            ) : (
              <AvatarFallback className="vf-text-body-s font-medium bg-muted text-muted-foreground">
                {member.name.split(" ").map(n => n[0]).join("").toUpperCase()}
              </AvatarFallback>
            )}
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="vf-text-body-l font-medium text-foreground truncate">{member.name}</p>
            <p className="vf-text-body-s text-muted-foreground truncate">{member.email}</p>
          </div>
          <StatusBadge variant="secondary">{member.role}</StatusBadge>
          {actions && <div className="flex-shrink-0">{actions(member)}</div>}
        </div>
      ))}
    </div>
  );
}
