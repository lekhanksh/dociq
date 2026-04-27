import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Skeleton } from "@/components/ui/skeleton";
import { DeptBadge, RoleBadge } from "@/components/DeptBadge";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Users, FileText, Database, Building2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface AdminStats {
  users: { email: string; name: string; role: string; department: string }[];
  total_users: number;
  total_documents: number;
  total_chunks: number;
  documents_by_department: Record<string, number>;
  recent_documents: { id: string; filename: string; department: string; uploaded_at: string }[];
}

function timeAgo(iso: string) {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function AdminDashboard() {
  const { token } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/admin/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setStats(await res.json());
    } catch (e) {
      toast.error("Failed to load admin stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStats(); }, [token]);

  const chartData = stats
    ? Object.entries(stats.documents_by_department).map(([dept, chunks]) => ({
        dept: dept.charAt(0).toUpperCase() + dept.slice(1),
        chunks,
      }))
    : [];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Admin Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Platform overview and user management</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchStats} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: Users, label: "Total Users", value: stats?.total_users },
          { icon: FileText, label: "Documents", value: stats?.total_documents },
          { icon: Database, label: "Chunks Indexed", value: stats?.total_chunks },
          { icon: Building2, label: "Departments", value: stats ? Object.keys(stats.documents_by_department).length : undefined },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="rounded-xl border border-border bg-card p-4 shadow-card">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Icon className="h-4 w-4 text-primary" />
              {label}
            </div>
            <div className="mt-2 text-2xl font-semibold text-foreground">
              {loading ? <Skeleton className="h-7 w-16" /> : (value ?? 0).toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chunks by department chart */}
        <div className="rounded-xl border border-border bg-card p-5 shadow-card">
          <h2 className="text-base font-semibold text-foreground">Chunks by Department</h2>
          <div className="mt-4 h-56">
            {loading ? (
              <Skeleton className="h-full w-full" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
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
            )}
          </div>
        </div>

        {/* Recent documents */}
        <div className="rounded-xl border border-border bg-card p-5 shadow-card">
          <h2 className="text-base font-semibold text-foreground">Recent Documents</h2>
          <div className="mt-3 space-y-2">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)
              : stats?.recent_documents.length === 0
              ? <p className="text-sm text-muted-foreground py-4 text-center">No documents yet</p>
              : stats?.recent_documents.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">{doc.filename}</p>
                      <DeptBadge dept={doc.department as any} />
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0 ml-3">{timeAgo(doc.uploaded_at)}</span>
                  </div>
                ))}
          </div>
        </div>
      </div>

      {/* Users table */}
      <div className="rounded-xl border border-border bg-card shadow-card">
        <div className="p-4 border-b border-border">
          <h2 className="text-base font-semibold text-foreground">Users</h2>
          <p className="text-xs text-muted-foreground mt-0.5">All users in your company</p>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Role</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading
                ? Array.from({ length: 3 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 4 }).map((_, j) => (
                        <TableCell key={j}><Skeleton className="h-5 w-24" /></TableCell>
                      ))}
                    </TableRow>
                  ))
                : stats?.users.map((u) => (
                    <TableRow key={u.email}>
                      <TableCell className="font-medium text-foreground">{u.name}</TableCell>
                      <TableCell className="text-muted-foreground">{u.email}</TableCell>
                      <TableCell><DeptBadge dept={u.department as any} /></TableCell>
                      <TableCell><RoleBadge role={u.role as any} /></TableCell>
                    </TableRow>
                  ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
