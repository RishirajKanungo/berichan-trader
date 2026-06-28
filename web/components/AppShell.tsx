"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Boxes, Calculator, Gauge, Repeat, TrendingUp } from "lucide-react";
import { AuthButton } from "./AuthButton";
import { SCALES, useScale } from "./scale";
import { THEMES, useTheme } from "./theme";

const NAV = [
  { href: "/", label: "Team Builder", icon: Boxes },
  { href: "/meta", label: "Meta", icon: TrendingUp },
  { href: "/speed", label: "Speed Tiers", icon: Gauge },
  { href: "/trade", label: "Trade", icon: Repeat },
  { href: "/calc", label: "Damage Calc", icon: Calculator },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { theme, setTheme } = useTheme();
  const { scale, setScale } = useScale();
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen">
      <aside className="surface sticky top-0 flex h-screen w-[210px] shrink-0 flex-col p-3">
        <div className="px-2 py-3">
          <div className="text-lg font-bold leading-tight">Berichan</div>
          <div className="accent-text text-lg font-bold leading-tight">Trader</div>
        </div>

        <nav className="mt-3 space-y-1">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className="nav-item" data-active={pathname === href}>
              <Icon size={18} /> {label}
            </Link>
          ))}
        </nav>

        <div className="mt-auto space-y-3">
          <AuthButton />
          <div>
            <div className="muted mb-1 px-2 text-xs">Appearance</div>
            <div className="grid grid-cols-3 gap-1">
              {THEMES.map((t) => (
                <button
                  key={t.key}
                  className="btn"
                  onClick={() => setTheme(t.key)}
                  style={theme === t.key ? { background: "var(--accent)", color: "var(--on-accent)", borderColor: "transparent" } : undefined}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="muted mb-1 px-2 text-xs">Display size</div>
            <div className="grid grid-cols-4 gap-1">
              {SCALES.map((s) => (
                <button
                  key={s.key}
                  className="btn px-1"
                  title={`Scale the whole app to ${s.label} — great for 4K / large displays`}
                  onClick={() => setScale(s.key)}
                  style={scale === s.key ? { background: "var(--accent)", color: "var(--on-accent)", borderColor: "transparent" } : undefined}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-x-hidden p-6">{children}</main>
    </div>
  );
}
