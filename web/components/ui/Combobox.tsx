"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/** Editable input with a filtered dropdown. The dropdown is rendered in a portal
 *  with fixed positioning so it never gets clipped by modal overflow or hidden
 *  behind sibling cards' stacking contexts (backdrop-filter). Allows free text. */
export function Combobox({
  value,
  onChange,
  options,
  placeholder,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder?: string;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value);
  const [rect, setRect] = useState<{ left: number; top: number; width: number } | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => setQuery(value), [value]);

  const reposition = () => {
    const r = inputRef.current?.getBoundingClientRect();
    if (r) setRect({ left: r.left, top: r.bottom + 4, width: r.width });
  };

  useLayoutEffect(() => {
    if (!open) return;
    reposition();
    const onScrollResize = () => reposition();
    window.addEventListener("scroll", onScrollResize, true);
    window.addEventListener("resize", onScrollResize);
    return () => {
      window.removeEventListener("scroll", onScrollResize, true);
      window.removeEventListener("resize", onScrollResize);
    };
  }, [open]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      const t = e.target as Node;
      if (wrapRef.current?.contains(t) || popRef.current?.contains(t)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const q = query.trim().toLowerCase();
  const filtered = (q ? options.filter((o) => o.toLowerCase().includes(q)) : options).slice(0, 60);

  const commit = (v: string) => {
    onChange(v);
    setQuery(v);
    setOpen(false);
  };

  return (
    <div className="relative" ref={wrapRef}>
      <input
        ref={inputRef}
        className="input"
        value={query}
        placeholder={placeholder}
        disabled={disabled}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange(e.target.value);
          setOpen(true);
        }}
      />
      {open && rect && filtered.length > 0 &&
        createPortal(
          <div
            ref={popRef}
            className="surface max-h-56 overflow-y-auto rounded-lg shadow-2xl"
            style={{ position: "fixed", left: rect.left, top: rect.top, width: rect.width, zIndex: 1000, background: "var(--surface)" }}
          >
            {filtered.map((opt) => (
              <button
                key={opt}
                type="button"
                className="block w-full px-3 py-1.5 text-left text-sm hover:bg-[var(--panel)]"
                onMouseDown={(e) => { e.preventDefault(); commit(opt); }}
              >
                {opt}
              </button>
            ))}
          </div>,
          document.body,
        )}
    </div>
  );
}
