const SUGGESTIONS = [
  "What are the key terms in our contracts?",
  "Summarize the latest HR policy changes",
  "What were last quarter's financial highlights?",
];

export function SuggestedPills({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex flex-wrap justify-center gap-2 max-w-2xl">
      {SUGGESTIONS.map((s) => (
        <button
          key={s}
          onClick={() => onPick(s)}
          className="rounded-full border border-border bg-card px-4 py-2 text-sm text-foreground/80 hover:border-primary/50 hover:text-primary hover:bg-primary/5 transition-colors shadow-card"
        >
          {s}
        </button>
      ))}
    </div>
  );
}