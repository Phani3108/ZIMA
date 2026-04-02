"use client";

import { WifiOff } from "lucide-react";

/**
 * Reusable offline banner for pages that need a backend.
 * Shows when backendOnline === false.
 */
export default function OfflineBanner({
  title = "Backend Offline",
  children,
}: {
  title?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="text-center py-16">
      <WifiOff size={40} className="mx-auto mb-3 text-amber-400" />
      <p className="text-gray-600 font-medium mb-1">{title}</p>
      {children || (
        <p className="text-sm text-gray-400 max-w-md mx-auto">
          This page requires a running backend. Deploy the API server and set{" "}
          <code className="bg-gray-100 px-1 rounded text-xs">NEXT_PUBLIC_API_URL</code> to enable this feature.
        </p>
      )}
    </div>
  );
}
