import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

export interface SidePanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  width?: "sm" | "md" | "lg" | "xl";
}

const widthMap = {
  sm: "sm:max-w-[350px]",
  md: "sm:max-w-[400px]",
  lg: "sm:max-w-[500px]",
  xl: "sm:max-w-[600px]",
};

export function SidePanel({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
  width = "md",
}: SidePanelProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className={cn("w-full sm:max-w-[400px] flex flex-col p-0", widthMap[width], className)}>
        <SheetHeader className="px-6 py-4 border-b border-border">
          <SheetTitle className="text-base font-semibold">{title}</SheetTitle>
          {description && <SheetDescription className="vf-text-body-m">{description}</SheetDescription>}
        </SheetHeader>
        <div className="flex-1 overflow-y-auto px-6 py-6">{children}</div>
        {footer && (
          <div className="px-6 py-4 border-t border-border flex items-center justify-end gap-3">
            {footer}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
