import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import { ToastProvider } from "@/components/ToastProvider";

export const metadata: Metadata = {
  title: "Zeta IMA — AI Marketing Agency",
  description: "Your autonomous AI marketing team",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden bg-gray-100">
        <ToastProvider>
          <Sidebar />
          <main className="flex-1 overflow-y-auto">{children}</main>
        </ToastProvider>
      </body>
    </html>
  );
}
