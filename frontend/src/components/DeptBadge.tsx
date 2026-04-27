import { cn } from "@/lib/utils";
import type { Dept } from "@/lib/jwt";

const LABEL: Record<Dept, string> = {
  hr: "HR",
  finance: "Finance",
  legal: "Legal",
  general: "General",
};

const STYLES: Record<Dept, string> = {
  hr: "bg-dept-hr/10 text-dept-hr border-dept-hr/30",
  finance: "bg-dept-finance/10 text-dept-finance border-dept-finance/30",
  legal: "bg-dept-legal/10 text-dept-legal border-dept-legal/30",
  general: "bg-dept-general/10 text-dept-general border-dept-general/40",
};

export function DeptBadge({ dept, className }: { dept: Dept; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        STYLES[dept],
        className,
      )}
    >
      {LABEL[dept]}
    </span>
  );
}

const ROLE_STYLES: Record<string, string> = {
  admin: "bg-primary/10 text-primary border-primary/30",
  uploader: "bg-info/10 text-info border-info/30",
  viewer: "bg-muted text-muted-foreground border-border",
};

export function RoleBadge({ role, className }: { role: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        ROLE_STYLES[role] ?? ROLE_STYLES.viewer,
        className,
      )}
    >
      {role}
    </span>
  );
}