"use client";

import { useEffect, useState } from "react";
import { loadData } from "@/lib/data";
import { AuthProvider } from "./auth";
import { ScaleProvider } from "./scale";
import { TeamProvider } from "./team";
import { ThemeProvider } from "./theme";

/** Loads the bundled datasets once, then renders the app (with theme + auth). */
export function AppProviders({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    loadData().then(() => setReady(true));
  }, []);

  return (
    <ThemeProvider>
      <ScaleProvider>
      <AuthProvider>
        <TeamProvider>
          {ready ? (
            children
          ) : (
            <div className="flex min-h-screen items-center justify-center">
              <div className="muted animate-pulse text-sm">Loading Pokédex…</div>
            </div>
          )}
        </TeamProvider>
      </AuthProvider>
      </ScaleProvider>
    </ThemeProvider>
  );
}
