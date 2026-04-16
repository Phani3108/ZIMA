"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Landing redirect — go to the first agent (Design Agent) by default */
export default function AgentIndexPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/future/agent/design"); }, [router]);

  return (
    <div className="flex items-center justify-center h-full">
      <p className="text-sm text-gray-400">Loading agent workspace...</p>
    </div>
  );
}
