import { Navigate, useLocation } from "react-router-dom";
import { useAuth, type Role } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { useEffect } from "react";

interface Props {
  children: React.ReactNode;
  requireRole?: Role;
}

export function ProtectedRoute({ children, requireRole }: Props) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (isAuthenticated && requireRole && user?.role !== requireRole) {
      toast.error("You don't have access to that page.");
    }
  }, [isAuthenticated, requireRole, user]);

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (requireRole && user?.role !== requireRole) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}