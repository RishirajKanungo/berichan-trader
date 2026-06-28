"use client";

import { createContext, useContext } from "react";
import { SessionProvider, useSession } from "next-auth/react";

/** Auth is opt-in: set NEXT_PUBLIC_AUTH_ENABLED=true once the providers + DB are
 *  configured. Until then the app runs with localStorage and no auth calls. */
export const AUTH_ENABLED = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

type AuthUser = { name?: string | null; image?: string | null; id?: string; login?: string };
type AuthState = { authEnabled: boolean; signedIn: boolean; user?: AuthUser; accessToken?: string };

const AuthContext = createContext<AuthState>({ authEnabled: false, signedIn: false });
export const useAuth = () => useContext(AuthContext);

function Bridge({ children }: { children: React.ReactNode }) {
  const { data } = useSession();
  return (
    <AuthContext.Provider
      value={{
        authEnabled: true,
        signedIn: !!data?.user,
        user: data?.user ?? undefined,
        accessToken: data?.accessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  if (!AUTH_ENABLED) {
    return <AuthContext.Provider value={{ authEnabled: false, signedIn: false }}>{children}</AuthContext.Provider>;
  }
  return (
    <SessionProvider>
      <Bridge>{children}</Bridge>
    </SessionProvider>
  );
}
