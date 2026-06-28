// Browser Twitch IRC client over WebSocket (wss://irc-ws.chat.twitch.tv:443).
// Ported from berichan/twitch_client.py — posts sets to chat and reads the
// queue/trade-confirmation messages. Whispers go through /api/whisper instead
// (Helix is CORS-blocked in the browser).

const IRC_WS = "wss://irc-ws.chat.twitch.tv:443";

export type ChatHandler = (sender: string, channel: string, text: string) => void;

export class TwitchChat {
  private ws: WebSocket | null = null;
  private handlers: ChatHandler[] = [];
  private channel = "";

  onMessage(handler: ChatHandler) {
    this.handlers.push(handler);
  }

  /** Connect, authenticate and JOIN. Resolves on the IRC welcome (001),
   *  rejects on auth failure or timeout. `token` is the raw access token. */
  connect(token: string, login: string, channel: string): Promise<void> {
    this.channel = channel.toLowerCase();
    return new Promise((resolve, reject) => {
      let settled = false;
      const ws = new WebSocket(IRC_WS);
      this.ws = ws;

      const timeout = setTimeout(() => {
        if (!settled) { settled = true; reject(new Error("IRC connect timed out.")); ws.close(); }
      }, 12000);

      ws.onopen = () => {
        ws.send(`PASS oauth:${token}`);
        ws.send(`NICK ${login.toLowerCase()}`);
        ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands");
        ws.send(`JOIN #${this.channel}`);
      };

      ws.onmessage = (ev) => {
        const data = typeof ev.data === "string" ? ev.data : "";
        for (const line of data.split("\r\n")) {
          if (!line) continue;
          if (line.startsWith("PING")) {
            ws.send(line.replace("PING", "PONG"));
            continue;
          }
          // Successful login → IRC welcome.
          if (!settled && / 001 /.test(line)) {
            settled = true;
            clearTimeout(timeout);
            resolve();
          }
          // Auth failure.
          if (!settled && /Login authentication failed|Improperly formatted auth/i.test(line)) {
            settled = true;
            clearTimeout(timeout);
            reject(new Error("Twitch login failed — your session may have expired. Sign out and back in."));
            ws.close();
            return;
          }
          this.dispatch(line);
        }
      };

      ws.onerror = () => {
        if (!settled) { settled = true; clearTimeout(timeout); reject(new Error("IRC connection error.")); }
      };
    });
  }

  private dispatch(line: string) {
    // Strip IRCv3 tags, then match :sender!user@host PRIVMSG #channel :text
    const stripped = line.replace(/^@\S+\s+/, "");
    const m = /^:(\w+)!\w+@[\w.]+\.tmi\.twitch\.tv PRIVMSG #(\w+) :(.+)$/.exec(stripped);
    if (m) {
      const [, sender, channel, text] = m;
      for (const h of this.handlers) h(sender, channel, text);
    }
  }

  sendChat(message: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(`PRIVMSG #${this.channel} :${message}`);
    }
  }

  close() {
    this.ws?.close();
    this.ws = null;
    this.handlers = [];
  }
}
