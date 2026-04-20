import "./globals.css";
import type { ReactNode } from "react";
import { DarkModeToggle } from "@/components/DarkModeToggle";

export const metadata = { title: "Clinical Monitoring Copilot" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased dark:bg-gray-900 dark:text-white">
        <div className="mx-auto max-w-screen-xl px-4 py-6 sm:px-6">
          <div className="flex justify-end mb-4">
            <DarkModeToggle />
          </div>
          {children}
        </div>
      </body>
    </html>
  );
}
