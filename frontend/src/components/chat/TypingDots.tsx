export function TypingDots() {
  return (
    <div className="flex items-center gap-1.5 px-1 py-2">
      <span className="h-2 w-2 rounded-full bg-muted-foreground/60 animate-typing-dot" style={{ animationDelay: "0ms" }} />
      <span className="h-2 w-2 rounded-full bg-muted-foreground/60 animate-typing-dot" style={{ animationDelay: "160ms" }} />
      <span className="h-2 w-2 rounded-full bg-muted-foreground/60 animate-typing-dot" style={{ animationDelay: "320ms" }} />
    </div>
  );
}