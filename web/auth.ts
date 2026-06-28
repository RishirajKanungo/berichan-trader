// Auth.js (NextAuth v5) configuration.
//
// Twitch is the primary sign-in (it's a Twitch trading tool); Google is offered
// too. Providers are only enabled when their credentials are present, so the app
// builds and runs with no auth configured (it falls back to localStorage).
//
// For trading, the Twitch login requests chat + whisper scopes and the user's
// access token + login are captured so the browser can open Twitch IRC and the
// /api/whisper relay can send the trade code.
//
// Required env when enabling auth:
//   AUTH_SECRET            (run: npx auth secret)
//   AUTH_TWITCH_ID / AUTH_TWITCH_SECRET   (Twitch dev console app)
//   AUTH_GOOGLE_ID / AUTH_GOOGLE_SECRET   (optional)

import NextAuth, { type NextAuthConfig } from "next-auth";
import Twitch from "next-auth/providers/twitch";
import Google from "next-auth/providers/google";

// Scopes needed to post in chat and whisper the trade code.
const TWITCH_SCOPES = "openid user:read:email chat:read chat:edit user:manage:whispers";

const providers: NextAuthConfig["providers"] = [];
if (process.env.AUTH_TWITCH_ID && process.env.AUTH_TWITCH_SECRET) {
  providers.push(
    Twitch({
      authorization: { params: { scope: TWITCH_SCOPES } },
    }),
  );
}
if (process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET) {
  providers.push(Google);
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  trustHost: true,
  callbacks: {
    async jwt({ token, account }) {
      // On sign-in, keep the Twitch access token and resolve the canonical
      // login + user id (needed for IRC NICK and whispers) via Helix.
      if (account?.access_token) {
        token.accessToken = account.access_token;
        try {
          const res = await fetch("https://api.twitch.tv/helix/users", {
            headers: {
              Authorization: `Bearer ${account.access_token}`,
              "Client-Id": process.env.AUTH_TWITCH_ID ?? "",
            },
          });
          const me = (await res.json())?.data?.[0];
          if (me) {
            token.login = me.login;
            token.sub = me.id;
          }
        } catch {
          // non-fatal; token still usable, login may be missing
        }
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        if (token.sub) session.user.id = token.sub;
        session.user.login = token.login as string | undefined;
      }
      session.accessToken = token.accessToken as string | undefined;
      return session;
    },
  },
});
