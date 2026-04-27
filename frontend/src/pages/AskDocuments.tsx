import { useEffect, useRef, useState } from "react";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { SuggestedPills } from "@/components/chat/SuggestedPills";
import { useAuth } from "@/contexts/AuthContext";
import { streamQuery, getDocuments, type QueryResult } from "@/lib/api";
import { FileStack, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

const DEPT_LABEL: Record<string, string> = { hr: "HR", finance: "Finance", legal: "Legal", general: "General" };

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: QueryResult["sources"];
}

export default function AskDocuments() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [hasDocuments, setHasDocuments] = useState<boolean | null>(null); // null = loading
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streaming]);

  // Check if any documents are uploaded
  useEffect(() => {
    if (!token) return;
    getDocuments(token)
      .then((res) => setHasDocuments(res.documents.length > 0))
      .catch(() => setHasDocuments(false));
  }, [token]);

  const send = async (question: string) => {
    if (!token || !user) return;
    const uMsg: Message = { id: crypto.randomUUID(), role: "user", content: question };
    const aId = crypto.randomUUID();
    const aMsg: Message = { id: aId, role: "assistant", content: "" };
    setMessages((m) => [...m, uMsg, aMsg]);
    setStreaming(true);

    try {
      await streamQuery(
        question,
        token,
        (chunk) => {
          setMessages((m) =>
            m.map((x) => (x.id === aId ? { ...x, content: x.content + chunk } : x)),
          );
        },
        undefined,
        (result) => {
          // Attach sources when streaming completes
          setMessages((m) =>
            m.map((x) => (x.id === aId ? { ...x, sources: result.sources } : x)),
          );
          if (result.sources?.length) {
            setHasDocuments(true);
          }
        },
      );
    } catch (e) {
      toast.error("Query failed. Please try again.");
      setMessages((m) => m.filter((x) => x.id !== aId));
    } finally {
      setStreaming(false);
    }
  };

  const deptLabel = user ? DEPT_LABEL[user.dept] : "";
  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {!hasMessages ? (
          <div className="h-full grid place-items-center px-4">
            <div className="flex flex-col items-center text-center max-w-2xl">
              <div className="grid h-16 w-16 place-items-center rounded-2xl bg-primary/10 text-primary mb-5">
                <FileStack className="h-8 w-8" />
              </div>
              <h2 className="text-2xl font-semibold text-foreground">Ask anything about your documents</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Answers are grounded in your <span className="font-medium text-foreground">{deptLabel}</span> knowledge base
              </p>

              {/* No documents warning */}
              {hasDocuments === false && (
                <div className="mt-6 rounded-xl border border-warning/30 bg-warning/5 px-5 py-4 text-sm text-left w-full max-w-sm">
                  <p className="font-medium text-foreground">No documents uploaded yet</p>
                  <p className="mt-1 text-muted-foreground">Upload documents first so the AI has something to reference.</p>
                  <Button
                    size="sm"
                    className="mt-3"
                    onClick={() => navigate("/upload")}
                  >
                    <Upload className="h-4 w-4 mr-1.5" />
                    Upload Documents
                  </Button>
                </div>
              )}

              {hasDocuments !== false && (
                <div className="mt-8">
                  <SuggestedPills onPick={send} />
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl px-4 py-6 space-y-4">
            {messages.map((m, i) => (
              <ChatMessage
                key={m.id}
                role={m.role}
                content={m.content}
                sources={m.sources}
                isStreaming={streaming && i === messages.length - 1 && m.role === "assistant"}
                deptLabel={deptLabel}
              />
            ))}
          </div>
        )}
      </div>
      <ChatInput onSend={send} disabled={streaming} />
    </div>
  );
}