import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Phone entry rule (owner, 5-Nov-26): keep digits only and at most 10 of them. */
export function phoneDigits(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, 10);
}

/** Joins class names; a later Tailwind class wins over an earlier one. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
