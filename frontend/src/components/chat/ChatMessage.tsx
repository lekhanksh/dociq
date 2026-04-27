import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { extractCitations, stripCitations } from "@/lib/citations";
import { CitationChip } from "./CitationChip";
import { TypingDots } from "./TypingDots";
import { cn } from "@/lib/utils";
import type { QueryResult } from "@/lib/api";

interface Props {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  deptLabel?: string;
  sources?: QueryResult["sources"];
}

export function ChatMessage({ role, content, isStreaming, deptLabel, sources }: Props) {
  const [expandedSource, setExpandedSource] = useState<number | null>(null);

  if (role === "user") {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground shadow-card">
          {content}
        </div>
      </div>
    );
  }

  const inlineCitations = extractCitations(content);
  const clean = stripCitations(content);
  const hasSources = sources && sources.length > 0;

  return (
    <div className="flex justify-start animate-fade-in">
      <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-card border border-border px-4 py-3 shadow-card">
        {clean.length === 0 && isStreaming ? (
          <TypingDots />
        ) : (
          <div className={cn("prose prose-sm max-w-none text-foreground", "prose-p:my-2 prose-ul:my-2 prose-li:my-0.5 prose-strong:text-foreground")}>
            <ReactMarkdown>{clean}</ReactMarkdown>
          </div>
        )}

        {/* Inline citations from text (mock/fallback) */}
        {!hasSources && inlineCitations.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {inlineCitations.map((c) => (
              <CitationChip key={c.raw} citation={c} />
            ))}
          </div>
        )}

        {/* Real sources from API — clickable to expand snippet (Req 6.3 / 6.4) */}
        {!isStreaming && hasSources && (
          <div className="mt-3 border-t border-border pt-3 space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Sources</p>
            {sources.map((src, i) => (
              <div key={i} className="rounded-lg bg-muted/50 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setExpandedSource(expandedSource === i ? null : i)}
                  className="w-full flex items-start gap-2 px-3 py-2 text-left hover:bg-muted/80 transition-colors"
                >
                  <span className="mt-0.5 shrink-0 grid h-4 w-4 place-items-center rounded-full bg-primary/15 text-primary text-[10px] font-bold">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-foreground truncate">{src.filename}</p>
                    <p className="text-xs text-muted-foreground capitalize">{src.department} · {Math.round(src.similarity * 100)}% match</p>
                  </div>
                  <span className="text-muted-foreground text-xs mt-0.5">{expandedSource === i ? "▲" : "▼"}</span>
                </button>
                {expandedSource === i && src.snippet && (
                  <div className="px-3 pb-3 pt-1 border-t border-border/50">
                    <p className="text-xs text-muted-foreground italic leading-relaxed">"{src.snippet}"</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {!isStreaming && (hasSources || inlineCitations.length > 0) && deptLabel && (
          <p className="mt-2 text-xs text-muted-foreground">
            Answered from your {deptLabel} collection · {hasSources ? sources.length : inlineCitations.length} source{(hasSources ? sources.length : inlineCitations.length) === 1 ? "" : "s"} used
          </p>
        )}
      </div>
    </div>
  );
}