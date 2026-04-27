import { useMemo, useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { getDocuments, type Document } from "@/lib/api";
import { DeptBadge } from "@/components/DeptBadge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { FileText, Database, Clock, ArrowUpDown, FolderOpen, Search, Trash2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

type SortKey = "filename" | "uploaded_at" | "chunks";

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function MyCollection() {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [docs, setDocs] = useState<Document[]>([]);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "uploaded_at", dir: "desc" });
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchDocs = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const response = await getDocuments(token);
      setDocs(response.documents);
    } catch {
      toast.error("Failed to load documents. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  const handleDelete = async (doc: Document) => {
    if (!token) return;
    setDeletingId(doc.id);
    try {
      const res = await fetch(`${BASE_URL}/documents/${doc.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as any).detail || `Delete failed (${res.status})`);
      }
      setDocs((prev) => prev.filter((d) => d.id !== doc.id));
      toast.success(`"${doc.filename}" deleted`);
    } catch (e) {
      toast.error((e as Error).message || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  const canDelete = user?.role === "admin" || user?.role === "uploader";
  const totalChunks = docs.reduce((s, d) => s + d.chunks, 0);
  const lastUpload = docs.length
    ? docs.reduce((a, b) => (new Date(a.uploaded_at) > new Date(b.uploaded_at) ? a : b)).uploaded_at
    : null;

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    let arr = q ? docs.filter((d) => d.filename.toLowerCase().includes(q)) : docs.slice();
    arr.sort((a, b) => {
      const dir = sort.dir === "asc" ? 1 : -1;
      if (sort.key === "chunks") return (a.chunks - b.chunks) * dir;
      if (sort.key === "uploaded_at")
        return (new Date(a.uploaded_at).getTime() - new Date(b.uploaded_at).getTime()) * dir;
      return a.filename.localeCompare(b.filename) * dir;
    });
    return arr;
  }, [docs, search, sort]);

  const toggleSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }));

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard icon={<FileText className="h-5 w-5" />} label="Total Documents" value={loading ? null : String(docs.length)} />
        <StatCard icon={<Database className="h-5 w-5" />} label="Total Chunks Indexed" value={loading ? null : totalChunks.toLocaleString()} />
        <StatCard icon={<Clock className="h-5 w-5" />} label="Last Upload" value={loading ? null : lastUpload ? timeAgo(lastUpload) : "—"} />
      </div>

      <div className="rounded-xl border border-border bg-card shadow-card">
        <div className="p-4 border-b border-border flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search documents..."
              className="pl-8"
            />
          </div>
          <Button variant="outline" size="sm" onClick={fetchDocs} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {loading ? (
          <div className="p-4 space-y-2">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : visible.length === 0 ? (
          <div className="p-12 text-center">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-muted text-muted-foreground">
              <FolderOpen className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-foreground">No documents uploaded yet</h3>
            <p className="mt-1 text-sm text-muted-foreground">Upload your first document to get started.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableTh label="File Name" active={sort.key === "filename"} dir={sort.dir} onClick={() => toggleSort("filename")} />
                  <TableHead>Department</TableHead>
                  <SortableTh label="Date" active={sort.key === "uploaded_at"} dir={sort.dir} onClick={() => toggleSort("uploaded_at")} />
                  <SortableTh label="Chunks" active={sort.key === "chunks"} dir={sort.dir} onClick={() => toggleSort("chunks")} />
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((d) => (
                  <TableRow key={d.id}>
                    <TableCell className="font-medium text-foreground">{d.filename}</TableCell>
                    <TableCell><DeptBadge dept={d.department as any} /></TableCell>
                    <TableCell className="text-muted-foreground">{timeAgo(d.uploaded_at)}</TableCell>
                    <TableCell className="text-muted-foreground">{d.chunks.toLocaleString()}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center rounded-full border border-success/30 bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
                        {d.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      {canDelete && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-destructive hover:text-destructive hover:bg-destructive/10"
                              disabled={deletingId === d.id}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete document?</AlertDialogTitle>
                              <AlertDialogDescription>
                                This will permanently delete <strong>{d.filename}</strong> and remove all {d.chunks} indexed chunks. This cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                onClick={() => handleDelete(d)}
                              >
                                Delete
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | null }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-card">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="text-primary">{icon}</span>
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-foreground">
        {value === null ? <Skeleton className="h-7 w-16" /> : value}
      </div>
    </div>
  );
}

function SortableTh({ label, active, dir, onClick }: { label: string; active: boolean; dir: "asc" | "desc"; onClick: () => void }) {
  return (
    <TableHead>
      <button onClick={onClick} className="inline-flex items-center gap-1 hover:text-foreground transition-colors">
        {label}
        <ArrowUpDown className={`h-3 w-3 ${active ? "text-primary" : "opacity-40"} ${active && dir === "asc" ? "rotate-180" : ""}`} />
      </button>
    </TableHead>
  );
}
