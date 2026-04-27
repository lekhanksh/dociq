import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { uploadFile } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Upload, FileText, FileType2, FileCode2, X, RefreshCw, CheckCircle2, AlertCircle, Lock } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { Dept } from "@/lib/jwt";

const ACCEPTED = [".pdf", ".docx", ".txt"];
const MAX_BYTES = 10 * 1024 * 1024;

type Status = "queued" | "uploading" | "indexed" | "failed";

interface QueueItem {
  id: string;
  file: File;
  progress: number;
  status: Status;
  error?: string;
  chunks?: number;
}

function fileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (ext === "pdf") return <FileText className="h-5 w-5 text-destructive" />;
  if (ext === "docx") return <FileType2 className="h-5 w-5 text-info" />;
  return <FileCode2 className="h-5 w-5 text-muted-foreground" />;
}

function formatSize(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

function validate(file: File): string | null {
  const ext = "." + (file.name.split(".").pop()?.toLowerCase() ?? "");
  if (!ACCEPTED.includes(ext)) return "File type not supported";
  if (file.size > MAX_BYTES) return "File exceeds 10MB limit";
  return null;
}

export default function UploadFiles() {
  const { user, token } = useAuth();
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [dragError, setDragError] = useState(false);
  const [dept, setDept] = useState<Dept>(user?.dept ?? "general");
  const inputRef = useRef<HTMLInputElement>(null);

  if (!user) return null;

  const isViewer = user.role === "viewer";
  const canChooseDept = user.role === "admin";

  const addFiles = (files: FileList | File[]) => {
    const next: QueueItem[] = [];
    let rejected = false;
    for (const f of Array.from(files)) {
      const err = validate(f);
      if (err) {
        rejected = true;
        toast.error(`${f.name}: ${err}`);
        continue;
      }
      next.push({ id: crypto.randomUUID(), file: f, progress: 0, status: "queued" });
    }
    if (rejected) {
      setDragError(true);
      setTimeout(() => setDragError(false), 1200);
    }
    if (next.length) setQueue((q) => [...q, ...next]);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (isViewer) return;
    addFiles(e.dataTransfer.files);
  };

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(e.target.files);
    e.target.value = "";
  };

  const remove = (id: string) => setQueue((q) => q.filter((x) => x.id !== id));

  const uploadOne = async (item: QueueItem) => {
    if (!token) return;
    setQueue((q) => q.map((x) => (x.id === item.id ? { ...x, status: "uploading", progress: 0, error: undefined } : x)));
    try {
      const res = await uploadFile(item.file, token, (pct) => {
        setQueue((q) => q.map((x) => (x.id === item.id ? { ...x, progress: pct } : x)));
      }, dept);
      setQueue((q) => q.map((x) => (x.id === item.id ? { ...x, status: "indexed", progress: 100, chunks: res.chunks_indexed } : x)));
      toast.success(`${item.file.name} indexed (${res.chunks_indexed} chunks)`);
    } catch (err) {
      setQueue((q) => q.map((x) => (x.id === item.id ? { ...x, status: "failed", error: (err as Error).message } : x)));
      toast.error(`${item.file.name}: upload failed`);
    }
  };

  const uploadAll = async () => {
    const pending = queue.filter((q) => q.status === "queued" || q.status === "failed");
    for (const it of pending) await uploadOne(it);
  };

  if (isViewer) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <div className="rounded-xl border border-warning/30 bg-warning/5 p-6 flex items-start gap-4">
          <Lock className="h-6 w-6 text-warning shrink-0 mt-0.5" />
          <div>
            <h2 className="text-base font-semibold text-foreground">Upload disabled</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              You don't have upload permission. Contact your admin to request access.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={cn(
          "rounded-xl border-2 border-dashed p-10 text-center transition-colors",
          dragOver ? "border-primary bg-primary/5" : "border-border bg-card",
          dragError && "border-destructive bg-destructive/5",
        )}
      >
        <div className="grid h-14 w-14 mx-auto place-items-center rounded-full bg-primary/10 text-primary">
          <Upload className="h-6 w-6" />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-foreground">Drag and drop files here</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Supports PDF, DOCX, TXT · Max 10MB per file
        </p>
        <Button
          variant="outline"
          className="mt-4 border-primary/40 text-primary hover:bg-primary/10 hover:text-primary"
          onClick={() => inputRef.current?.click()}
        >
          Browse Files
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={onPick}
        />
      </div>

      {queue.length > 0 && (
        <>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-foreground">Upload to department:</span>
              <Select value={dept} onValueChange={(v) => setDept(v as Dept)} disabled={!canChooseDept}>
                <SelectTrigger className="w-44">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hr">HR</SelectItem>
                  <SelectItem value="finance">Finance</SelectItem>
                  <SelectItem value="legal">Legal</SelectItem>
                  <SelectItem value="general">General</SelectItem>
                </SelectContent>
              </Select>
              {!canChooseDept && (
                <span className="text-xs text-muted-foreground">Locked to your department</span>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card divide-y divide-border">
            {queue.map((item) => (
              <div key={item.id} className="p-4 flex items-center gap-4">
                {fileIcon(item.file.name)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-3">
                    <div className="truncate text-sm font-medium text-foreground">{item.file.name}</div>
                    <StatusBadge status={item.status} />
                  </div>
                  <div className="mt-0.5 text-xs text-muted-foreground">
                    {formatSize(item.file.size)}
                    {item.chunks ? ` · ${item.chunks} chunks` : ""}
                  </div>
                  {item.status === "uploading" && (
                    <Progress value={item.progress} className="mt-2 h-1.5" />
                  )}
                </div>
                {item.status === "failed" && (
                  <Button size="sm" variant="ghost" onClick={() => uploadOne(item)}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                )}
                <Button size="icon" variant="ghost" onClick={() => remove(item.id)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          <div className="flex justify-end">
            <Button onClick={uploadAll} disabled={!queue.some((q) => q.status === "queued" || q.status === "failed")}>
              Upload All
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: Status }) {
  const map: Record<Status, { label: string; cls: string; icon?: React.ReactNode }> = {
    queued: { label: "Queued", cls: "bg-muted text-muted-foreground border-border" },
    uploading: { label: "Uploading...", cls: "bg-info/10 text-info border-info/30" },
    indexed: { label: "Indexed", cls: "bg-success/10 text-success border-success/30", icon: <CheckCircle2 className="h-3 w-3" /> },
    failed: { label: "Failed", cls: "bg-destructive/10 text-destructive border-destructive/30", icon: <AlertCircle className="h-3 w-3" /> },
  };
  const v = map[status];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium", v.cls)}>
      {v.icon}
      {v.label}
    </span>
  );
}