import { ArrowUp } from "lucide-react";
import { useState, useRef, useEffect, type KeyboardEvent } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const submit = () => {
    const v = value.trim();
    if (!v || disabled) return;
    onSend(v);
    setValue("");
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-border bg-background px-4 py-4">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-xl border border-border bg-card p-2 shadow-card focus-within:border-primary/60 transition-colors">
          <textarea
            ref={ref}
            rows={1}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ask a question about your documents..."
            className="flex-1 resize-none bg-transparent px-2 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            disabled={disabled}
          />
          <button
            onClick={submit}
            disabled={disabled || !value.trim()}
            className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground hover:bg-primary-dark disabled:opacity-40 disabled:pointer-events-none transition-colors"
            aria-label="Send"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-2 text-center text-xs text-muted-foreground">
          Answers are limited to documents in your department collection
        </p>
      </div>
    </div>
  );
}