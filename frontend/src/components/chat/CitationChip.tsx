import { toast } from "sonner";
import type { Citation } from "@/lib/citations";

export function CitationChip({ citation }: { citation: Citation }) {
  return (
    <button
      type="button"
      onClick={() =>
        toast(`Source: ${citation.filename} — Page ${citation.page}`, {
          description: "Opening source...",
        })
      }
      className="inline-flex items-center gap-1 rounded-full border border-primary/60 bg-card px-2.5 py-0.5 text-xs font-medium text-primary hover:bg-primary/10 transition-colors"
    >
      <span className="truncate max-w-[200px]">{citation.filename}</span>
      <span className="opacity-60">·</span>
      <span>Page {citation.page}</span>
    </button>
  );
}