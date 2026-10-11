export type ChipTone = "ok" | "warn" | "error" | "info" | "spa" | "neutral";

export function StatusChip({ tone = "neutral", children }: {
  tone?: ChipTone;
  children: string;
}) {
  return <span className={`chip chip-${tone}`}>{children}</span>;
}
