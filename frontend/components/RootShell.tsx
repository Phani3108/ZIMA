"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";

/**
 * Conditionally renders the main Sidebar for non-future routes.
 * `/future/*` routes use their own AgentSidebar via the nested layout.
 */
export default function RootShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const isFuture = path?.startsWith("/future");

  if (isFuture) {
    // Future routes provide their own layout — render children bare
    return <>{children}</>;
  }

  return (
    <>
      <Sidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </>
  );
}
