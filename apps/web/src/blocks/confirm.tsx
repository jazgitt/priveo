import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/ui/alert-dialog";

export interface ConfirmOptions {
  title: string;
  /** What will happen, in a sentence or two. */
  description: ReactNode;
  confirmLabel: string;
  /** "danger" for anything that removes, ends or signs out. */
  tone?: "default" | "danger";
}

type Ask = (o: ConfirmOptions) => Promise<boolean>;
const ConfirmContext = createContext<Ask | null>(null);

/**
 * One confirmation dialog for the whole portal. `await confirm({...})` is true
 * when the admin presses the confirm button, false on Cancel or Escape.
 */
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [asked, setAsked] = useState<ConfirmOptions | null>(null);
  const answer = useRef<(ok: boolean) => void>(() => {});

  const confirm = useCallback<Ask>((o) => new Promise<boolean>((resolve) => {
    answer.current = resolve;
    setAsked(o);
  }), []);

  const close = (ok: boolean) => {
    answer.current(ok);
    answer.current = () => {};
    setAsked(null);
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <AlertDialog open={asked !== null} onOpenChange={(open) => { if (!open) close(false); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{asked?.title}</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div>{asked?.description}</div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => close(false)}>Cancel</AlertDialogCancel>
            <AlertDialogAction variant={asked?.tone === "danger" ? "destructive" : "default"}
                               onClick={() => close(true)}>
              {asked?.confirmLabel}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ConfirmContext.Provider>
  );
}

export function useConfirm(): Ask {
  const v = useContext(ConfirmContext);
  if (!v) throw new Error("useConfirm needs a ConfirmProvider");
  return v;
}
