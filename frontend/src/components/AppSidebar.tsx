import { MessageCircle, Upload, FolderOpen, BarChart3, LayoutDashboard, LogOut } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { DocIQLogo } from "./DocIQLogo";
import { DeptBadge, RoleBadge } from "./DeptBadge";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const NAV = [
  { to: "/", icon: MessageCircle, label: "Ask Documents", end: true },
  { to: "/upload", icon: Upload, label: "Upload Files" },
  { to: "/collection", icon: FolderOpen, label: "My Collection" },
];

export function AppSidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const initials = user.name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const linkClass =
    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground";
  const activeClass = "bg-sidebar-accent text-sidebar-foreground font-medium";

  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border">
      <div className="px-4 py-5">
        <DocIQLogo />
      </div>

      <div className="px-4 pb-4">
        <div className="rounded-lg bg-sidebar-accent/60 p-3">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-primary text-primary-foreground text-sm font-semibold">
              {initials}
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-medium">{user.name}</div>
              <div className="truncate text-xs text-sidebar-foreground/60">{user.email}</div>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <DeptBadge dept={user.dept} />
            <RoleBadge role={user.role} />
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => cn(linkClass, isActive && activeClass)}
          >
            <item.icon className="h-4 w-4" />
            <span>{item.label}</span>
          </NavLink>
        ))}

        {user.role === "admin" && (
          <>
            <div className="my-3 border-t border-sidebar-border" />
            <NavLink
              to="/admin"
              className={({ isActive }) => cn(linkClass, isActive && activeClass)}
            >
              <LayoutDashboard className="h-4 w-4" />
              <span>Admin Dashboard</span>
            </NavLink>
            <NavLink
              to="/stats"
              className={({ isActive }) => cn(linkClass, isActive && activeClass)}
            >
              <BarChart3 className="h-4 w-4" />
              <span>Collection Stats</span>
            </NavLink>
          </>
        )}
      </nav>

      <div className="p-3 border-t border-sidebar-border">
        <button
          onClick={() => {
            logout();
            toast.success("Signed out");
            navigate("/login");
          }}
          className={cn(linkClass, "w-full")}
        >
          <LogOut className="h-4 w-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}