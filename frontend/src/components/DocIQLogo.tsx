import { FileSearch } from "lucide-react";
import { cn } from "@/lib/utils";

export function DocIQLogo({ size = 32, withText = true, className }: { size?: number; withText?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="grid place-items-center rounded-lg bg-primary text-primary-foreground shadow-card"
        style={{ width: size, height: size }}
      >
        <FileSearch style={{ width: size * 0.6, height: size * 0.6 }} />
      </div>
      {withText && (
        <div className="flex items-baseline gap-1.5">
          <span className="text-lg font-semibold tracking-tight">DocIQ</span>
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">v1.0</span>
        </div>
      )}
    </div>
  );
}