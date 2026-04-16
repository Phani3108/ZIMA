import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/ToastProvider";
import RootShell from "@/components/RootShell";

export const metadata: Metadata = {
  title: "Zeta IMA — AI Marketing Agency",
  description: "Your autonomous AI marketing team",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden bg-gray-100">
        <ToastProvider>
          <RootShell>{children}</RootShell>
        </ToastProvider>
      </body>
    </html>
  );
}
