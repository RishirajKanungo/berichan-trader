// Serverless relay for Twitch whispers (Helix is CORS-blocked in browsers).
// Sends the trade code from the signed-in user to the bot. Reads the user's
// access token from the server session — the browser never has to forward it.

import { NextResponse } from "next/server";
import { auth } from "@/auth";

const HELIX = "https://api.twitch.tv/helix";

export async function POST(req: Request) {
  const session = await auth();
  const token = session?.accessToken;
  const fromId = session?.user?.id;
  const clientId = process.env.AUTH_TWITCH_ID;

  if (!token || !fromId) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  if (!clientId) return NextResponse.json({ error: "server-misconfigured" }, { status: 500 });

  const { toLogin, message } = await req.json();
  if (!toLogin || !message) return NextResponse.json({ error: "bad-request" }, { status: 400 });

  const headers = { Authorization: `Bearer ${token}`, "Client-Id": clientId };

  // Resolve the bot's user id.
  let toId: string | undefined;
  try {
    const r = await fetch(`${HELIX}/users?login=${encodeURIComponent(String(toLogin).toLowerCase())}`, { headers });
    toId = (await r.json())?.data?.[0]?.id;
  } catch {
    return NextResponse.json({ error: "lookup-failed" }, { status: 502 });
  }
  if (!toId) return NextResponse.json({ error: "bot-not-found" }, { status: 404 });

  // Send the whisper.
  const res = await fetch(`${HELIX}/whispers?from_user_id=${fromId}&to_user_id=${toId}`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ message: String(message) }),
  });

  if (res.status === 204) return NextResponse.json({ ok: true });
  const body = await res.text();
  return NextResponse.json({ error: "whisper-failed", status: res.status, detail: body }, { status: 502 });
}
