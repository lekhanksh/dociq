import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { DocIQLogo } from "@/components/DocIQLogo";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Loader2, AlertCircle, Info } from "lucide-react";

const ERROR_MESSAGES: Record<string, string> = {
  "Invalid email, password, or company slug": "Check your email, password, and company slug — all three must match.",
  "Network error": "Cannot reach the server. Make sure the backend is running.",
  default: "Login failed. Please try again.",
};

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companySlug, setCompanySlug] = useState("demo-company");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true });
  }, [isAuthenticated, navigate]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password.trim() || !companySlug.trim()) {
      setError("All fields are required.");
      return;
    }

    setLoading(true);
    try {
      const ok = await login(email.trim(), password, companySlug.trim());
      if (ok) {
        toast.success("Signed in successfully");
        navigate("/", { replace: true });
      } else {
        setError(ERROR_MESSAGES["Invalid email, password, or company slug"]);
      }
    } catch (err) {
      const msg = (err as Error).message || "";
      setError(ERROR_MESSAGES[msg] || ERROR_MESSAGES.default);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full grid place-items-center bg-sidebar p-4">
      <main className="w-full max-w-md animate-fade-in">
        <div className="mb-8 flex justify-center">
          <DocIQLogo size={44} className="[&_span]:text-sidebar-foreground" />
        </div>

        <div className="rounded-xl border border-sidebar-border bg-sidebar-accent/40 p-6 shadow-card">
          <h1 className="text-xl font-semibold text-sidebar-foreground">Sign in to DocIQ</h1>
          <p className="mt-1 text-sm text-sidebar-foreground/60">
            Enterprise document intelligence — private &amp; secure
          </p>

          {error && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={onSubmit} className="mt-5 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sidebar-foreground/80">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(null); }}
                placeholder="you@company.com"
                className="bg-sidebar text-sidebar-foreground border-sidebar-border placeholder:text-sidebar-foreground/40"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sidebar-foreground/80">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(null); }}
                placeholder="••••••••"
                className="bg-sidebar text-sidebar-foreground border-sidebar-border placeholder:text-sidebar-foreground/40"
              />
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Label htmlFor="companySlug" className="text-sidebar-foreground/80">Company Slug</Label>
                <span className="group relative">
                  <Info className="h-3.5 w-3.5 text-sidebar-foreground/40 cursor-help" />
                  <span className="pointer-events-none absolute left-5 top-0 z-10 w-52 rounded-lg border border-sidebar-border bg-sidebar px-2.5 py-2 text-xs text-sidebar-foreground/80 opacity-0 group-hover:opacity-100 transition-opacity shadow-lg">
                    Your company's unique identifier, e.g. <strong>acme-corp</strong>. For the demo use <strong>demo-company</strong>.
                  </span>
                </span>
              </div>
              <Input
                id="companySlug"
                type="text"
                autoComplete="organization"
                required
                value={companySlug}
                onChange={(e) => { setCompanySlug(e.target.value); setError(null); }}
                placeholder="demo-company"
                className="bg-sidebar text-sidebar-foreground border-sidebar-border placeholder:text-sidebar-foreground/40"
              />
              <p className="text-xs text-sidebar-foreground/50">
                Use <code className="bg-sidebar-accent/60 px-1 rounded">demo-company</code> for the demo environment
              </p>
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <><Loader2 className="h-4 w-4 animate-spin mr-2" />Signing in...</> : "Sign In"}
            </Button>
          </form>
        </div>

        <details className="mt-4 rounded-lg border border-sidebar-border bg-sidebar-accent/20 p-3 text-xs text-sidebar-foreground/70">
          <summary className="cursor-pointer text-sidebar-foreground/80 font-medium">Demo accounts</summary>
          <ul className="mt-2 space-y-1.5 font-mono">
            <li className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-primary shrink-0" />
              admin@dociq.com / demo123 — Admin · all departments
            </li>
            <li className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-info shrink-0" />
              sarah@dociq.com / demo123 — Finance · uploader
            </li>
            <li className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-muted-foreground shrink-0" />
              viewer@dociq.com / demo123 — HR · viewer
            </li>
          </ul>
          <p className="mt-2 text-sidebar-foreground/50">Company slug: <code className="bg-sidebar-accent/60 px-1 rounded">demo-company</code></p>
        </details>
      </main>
    </div>
  );
}
