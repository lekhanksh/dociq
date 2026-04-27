import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { getCollectionsInfo, type CollectionsInfo } from "@/lib/api";
import { mockActivity } from "@/lib/mockData";
import { DeptBadge } from "@/components/DeptBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Building2, DollarSign, Scale, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const ACTION_STYLES: Record<string, string> = {
  Uploaded: "bg-info/10 text-info border-info/30",
  Queried: "bg-success/10 text-success border-success/30",
  Deleted: "bg-destructive/10 text-destructive border-destructive/30",
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export default function CollectionStats() {
  const { token } = useAuth();
  const [info, setInfo] = useState<CollectionsInfo | null>(null);

  useEffect(() => {
    if (!token) return;
    getCollectionsInfo(token).then(setInfo).catch(() => setInfo(null));
  }, [token]);

  const cards = [
    { key: "hr" as const, label: "HR Collection", icon: Users },
    { key: "finance" as const, label: "Finance Collection", icon: DollarSign },
    { key: "legal" as const, label: "Legal Collection", icon: Scale },
    { key: "general" as const, label: "General Collection", icon: Building2 },
  ];

  const chartData = info
    ? [
        { dept: "HR", chunks: info.hr },
        { dept: "Finance", chunks: info.finance },
        { dept: "Legal", chunks: info.legal },
        { dept: "General", chunks: info.general },
      ]
    : [];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.key} className="rounded-xl border border-border bg-card p-4 shadow-card">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <c.icon className="h-4 w-4 text-primary" />
              {c.label}
            </div>
            <div className="mt-2 text-2xl font-semibold text-foreground">
              {info ? info[c.key].toLocaleString() : <Skeleton className="h-7 w-16" />}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">chunks indexed</div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-border bg-card p-5 shadow-card">
        <h2 className="text-base font-semibold text-foreground">Document chunks by department</h2>
        <p className="text-xs text-muted-foreground mt-0.5">Distribution across all collections</p>
        <div className="mt-4 h-72">
          {info ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="dept" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="chunks" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Skeleton className="h-full w-full" />
          )}
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card shadow-card">
        <div className="p-4 border-b border-border">
          <h2 className="text-base font-semibold text-foreground">Recent activity</h2>
          <p className="text-xs text-muted-foreground mt-0.5">Last 20 actions across the platform</p>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Document</TableHead>
                <TableHead className="text-right">Timestamp</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockActivity.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium text-foreground">{a.user}</TableCell>
                  <TableCell>
                    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", ACTION_STYLES[a.action])}>
                      {a.action}
                    </span>
                  </TableCell>
                  <TableCell><DeptBadge dept={a.dept} /></TableCell>
                  <TableCell className="text-muted-foreground">{a.document}</TableCell>
                  <TableCell className="text-right text-muted-foreground">{timeAgo(a.timestamp)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}