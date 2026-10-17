import { Copy, TriangleAlert } from "lucide-react";
import { useState } from "react";

import { useToast } from "@/components";
import { showDate } from "@/components/format";
import { Button } from "@/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/ui/dialog";

import type { CrewPassword, ReleasedJob } from "./api";

/** The generated password, once. Only the button closes it, so a stray click
 *  or Escape does not lose the password. */
export function PasswordDialog({ issued, onDone }: { issued: CrewPassword; onDone: () => void }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`Login ID: ${issued.login_id}\nPassword: ${issued.password}`);
      setCopied(true);
      toast.show("Copied to the clipboard.", "ok");
    } catch {
      toast.show("Could not copy. Write the password down.", "error");
    }
  };
  return (
    <Dialog open>
      <DialogContent showCloseButton={false} className="bg-card sm:max-w-md"
                     onEscapeKeyDown={(e) => e.preventDefault()} onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>Login for the crew member</DialogTitle>
          <DialogDescription className="sr-only">The new login ID and password.</DialogDescription>
        </DialogHeader>
        <p role="alert" className="m-0 flex gap-2 rounded-md bg-warn/10 px-3 py-2 text-sm text-[#7a4f0f]">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>This password is shown once. It cannot be seen again. Give it to the crew member yourself. Do not send it by SMS or WhatsApp.</span>
        </p>
        <dl className="m-0 grid grid-cols-[6rem_minmax(0,1fr)] gap-y-2 rounded-lg border bg-muted/40 p-4 text-sm">
          <dt className="text-muted-foreground">Name</dt><dd className="m-0 font-medium">{issued.crew.name}</dd>
          <dt className="text-muted-foreground">Login ID</dt><dd className="m-0 font-medium tabular-nums">{issued.login_id}</dd>
          <dt className="text-muted-foreground">Password</dt>
          <dd className="m-0 text-base font-semibold tracking-wide" data-testid="issued-password">{issued.password}</dd>
        </dl>
        <DialogFooter>
          <Button variant="outline" onClick={() => void copy()}><Copy aria-hidden />{copied ? "Copied" : "Copy"}</Button>
          <Button onClick={onDone}>I have noted it</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Jobs a change put on the Needs scheduling list (ADM-CRW-12). */
export function ReleasedJobs({ jobs }: { jobs: ReleasedJob[] }) {
  if (jobs.length === 0) return null;
  return (
    <div role="status" className="mt-4 rounded-lg border border-warn/40 bg-warn/5 px-4 py-3 text-sm">
      <p className="m-0 font-medium">{jobs.length} job{jobs.length === 1 ? "" : "s"} went to Needs scheduling.</p>
      <ul className="mt-1 mb-0">
        {jobs.map((j) => <li key={j.job_id}>{showDate(j.date)}: {j.service}, {j.registration}</li>)}
      </ul>
    </div>
  );
}
