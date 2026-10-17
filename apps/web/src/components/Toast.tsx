import { useMemo, type ReactNode } from "react";
import { toast } from "sonner";

import { Toaster } from "@/ui/sonner";

type Tone = "ok" | "error" | "info";
interface ToastApi { show: (text: string, tone?: Tone) => void }

/** The toast host. Toasts come from Sonner; `useToast` keeps the older call shape. */
export function ToastProvider({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <Toaster />
    </>
  );
}

export function useToast(): ToastApi {
  return useMemo(() => ({
    show: (text: string, tone: Tone = "info") => {
      if (tone === "ok") toast.success(text);
      else if (tone === "error") toast.error(text);
      else toast.info(text);
    },
  }), []);
}
