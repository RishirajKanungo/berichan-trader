import type { Metadata } from "next";
import "./globals.css";
import { AppProviders } from "@/components/AppProviders";

export const metadata: Metadata = {
  title: "Berichan Trader — Team Builder",
  description:
    "Build Pokémon Champions teams in your browser: full legal roster, items, moves, abilities, and the Stat-Point editor.",
};

// Set the saved theme + UI scale before paint to avoid a flash of the wrong one.
const themeInit = `(function(){try{var t=localStorage.getItem('berichan.theme')||'material';document.documentElement.setAttribute('data-theme',t);var s=localStorage.getItem('berichan.uiScale');if(s&&s!=='1')document.documentElement.style.zoom=s;}catch(e){document.documentElement.setAttribute('data-theme','material');}})();`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="material" className="h-full antialiased">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="min-h-full">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
