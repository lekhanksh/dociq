import { createContext, useCallback, useContext, useMemo, useState, useEffect, type ReactNode } from "react";
import { encodeJwt, decodeJwt, type JwtPayload, type Role, type Dept } from "@/lib/jwt";
import { login as apiLogin, getCurrentUser, getStoredToken, setStoredToken, clearStoredToken, type LoginRequest, type UserResponse } from "@/lib/auth";

interface DemoAccount {
  email: string;
  password: string;
  payload: JwtPayload;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    email: "sarah@dociq.com",
    password: "demo123",
    payload: { sub: "u_sarah", dept: "finance", role: "uploader", name: "Sarah Chen", email: "sarah@dociq.com" },
  },
  {
    email: "viewer@dociq.com",
    password: "demo123",
    payload: { sub: "u_alex", dept: "hr", role: "viewer", name: "Alex Roy", email: "viewer@dociq.com" },
  },
  {
    email: "admin@dociq.com",
    password: "demo123",
    payload: { sub: "u_priya", dept: "general", role: "admin", name: "Priya Mehta", email: "admin@dociq.com" },
  },
];

interface AuthState {
  token: string | null;
  user: JwtPayload | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string, companySlug?: string) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ token: null, user: null, isLoading: true });

  // Check for existing token on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredToken();
      if (token) {
        try {
          // Try to validate with backend first
          const user = await getCurrentUser();
          const userPayload = {
            sub: user.id,
            name: user.full_name || user.email,
            email: user.email,
            dept: user.department,
            role: user.role as Role,
          };
          setState({ token, user: userPayload, isLoading: false });
        } catch (error) {
          // Fallback to demo mode or clear token
          clearStoredToken();
          setState({ token: null, user: null, isLoading: false });
        }
      } else {
        setState({ token: null, user: null, isLoading: false });
      }
    };

    initAuth();
  }, []);

  const login = useCallback(async (email: string, password: string, companySlug = 'demo-company'): Promise<boolean> => {
    try {
      // Try backend authentication first
      const loginData: LoginRequest = { email, password, company_slug: companySlug };
      const response = await apiLogin(loginData);
      
      const userPayload = {
        sub: response.user.id,
        name: response.user.full_name || response.user.email,
        email: response.user.email,
        dept: response.user.department,
        role: response.user.role as Role,
      };
      
      setState({ token: response.access_token, user: userPayload, isLoading: false });
      return true;
    } catch (error) {
      // Fallback to demo accounts
      await new Promise((r) => setTimeout(r, 350));
      const acc = DEMO_ACCOUNTS.find(
        (a) => a.email.toLowerCase() === email.toLowerCase() && a.password === password,
      );
      if (!acc) return false;
      const token = encodeJwt(acc.payload);
      const user = decodeJwt(token);
      setState({ token, user, isLoading: false });
      return true;
    }
  }, []);

  const logout = useCallback(() => {
    clearStoredToken();
    setState({ token: null, user: null, isLoading: false });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, logout, isAuthenticated: !!state.token }),
    [state, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export type { Role, Dept, JwtPayload };