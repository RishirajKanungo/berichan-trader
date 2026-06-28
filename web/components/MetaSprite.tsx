"use client";

import { useState } from "react";
import { getSpecies } from "@/lib/data";
import { spriteUrl } from "@/lib/assets";
import { remoteSpriteUrl } from "@/lib/meta";

/**
 * Sprite for a competitive (meta) Pokémon. Prefers the bundled local sprite when
 * the name maps to a Champions species; otherwise (forms the roster names
 * differently) falls back to the upstream asset. Swaps to the remote on load
 * error so nothing renders broken.
 */
export function MetaSprite({ name, size = 56, className }: { name: string; size?: number; className?: string }) {
  const local = getSpecies(name);
  const [src, setSrc] = useState(local ? spriteUrl(local.id) : remoteSpriteUrl(name));
  const remote = remoteSpriteUrl(name);
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={name}
      width={size}
      height={size}
      className={className}
      style={{ imageRendering: "auto" }}
      onError={() => { if (src !== remote) setSrc(remote); }}
    />
  );
}
