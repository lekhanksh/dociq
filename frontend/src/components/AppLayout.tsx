import { Outlet, useLocation } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { Topbar } from "./Topbar";

export function AppLayout() {
  const { pathname } = useLocation();
  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      <AppSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main key={pathname} className="flex-1 overflow-auto animate-fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  );
}