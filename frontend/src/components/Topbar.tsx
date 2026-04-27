import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { DeptBadge, RoleBadge } from "./DeptBadge";
import { getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

const TITLES: Record<string, string> = {
  "/": "Ask Documents",
  "/upload": "Upload Files",
  "/collection": "My Collection",
  "/stats": "Collection Stats",
};

export function Topbar() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const r = await getHealth();
        if (!cancelled) setHealthy(r.status === "ok");
      } catch {
        if (!cancelled) setHealthy(false);
      }
    };
    check();
    const id = setInterval(check, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <header className="h-12 shrink-0 bg-card border-b border-border flex items-center px-4 justify-between">
      <div className="flex items-center gap-2.5">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            healthy === null ? "bg-muted" : healthy ? "bg-success" : "bg-destructive",
          )}
          title={healthy ? "Service healthy" : healthy === false ? "Service unreachable" : "Checking..."}
        />
        <h1 className="text-sm font-semibold text-foreground">{TITLES[pathname] ?? "DocIQ"}</h1>
      </div>
      {user && (
        <div className="flex items-center gap-2">
          <DeptBadge dept={user.dept} />
          <RoleBadge role={user.role} />
        </div>
      )}
    </header>
  );
}