import type { FormEvent, ReactNode } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/ui/dialog";

/**
 * A focused form in a dialog, with its own Save and Cancel. Saved values stay
 * on the page behind it until Save works, so typed and saved values never mix.
 */
export function FormDialog({
  open, onOpenChange, title, description, submitLabel, onSubmit, busy, disabled, danger,
  children, size = "md", extraActions, cancelLabel = "Cancel",
}: {
  /** null hides the Cancel button, for a dialog whose only button closes it. */
  cancelLabel?: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: ReactNode;
  submitLabel: string;
  onSubmit: () => void;
  busy?: boolean;
  disabled?: boolean;
  danger?: boolean;
  children: ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
  extraActions?: ReactNode;
}) {
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!busy && !disabled) onSubmit();
  };
  const width = { sm: "sm:max-w-md", md: "sm:max-w-lg", lg: "sm:max-w-2xl", xl: "sm:max-w-3xl" }[size];
  return (
    <Dialog open={open} onOpenChange={(o) => { if (!busy) onOpenChange(o); }}>
      <DialogContent className={cn("max-h-[90vh] overflow-y-auto bg-card", width)}>
        <form onSubmit={submit} className="flex flex-col gap-5">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            {description ? <DialogDescription>{description}</DialogDescription>
              : <DialogDescription className="sr-only">{title}</DialogDescription>}
          </DialogHeader>
          <div className="flex flex-col gap-4">{children}</div>
          <DialogFooter className="gap-2">
            {extraActions && <div className="mr-auto flex gap-2">{extraActions}</div>}
            {cancelLabel !== null && (
              <Button type="button" variant="outline" disabled={busy} onClick={() => onOpenChange(false)}>
                {cancelLabel}
              </Button>
            )}
            <Button type="submit" variant={danger ? "destructive" : "default"} disabled={busy || disabled}
                    aria-busy={busy || undefined}>
              {busy && <Loader2 className="animate-spin" aria-hidden />}
              {submitLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** A button that shows a spinner while its action runs. */
export function BusyButton({ busy, children, disabled, ...rest }: React.ComponentProps<typeof Button> & { busy?: boolean }) {
  return (
    <Button disabled={busy || disabled} aria-busy={busy || undefined} {...rest}>
      {busy && <Loader2 className="animate-spin" aria-hidden />}
      {children}
    </Button>
  );
}
