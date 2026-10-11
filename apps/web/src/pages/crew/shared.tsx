import { useState } from "react";

import { Button, Dialog, useToast } from "../../components";
import { showDate } from "../../components/format";
import type { CrewPassword, ReleasedJob } from "./api";

const ignore = () => {};

/** The generated password, once. Only the button closes it, so a stray click
 *  outside does not lose the password. */
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
    <Dialog open title="Login for the crew member" onClose={ignore}
            footer={<>
              <Button variant="secondary" onClick={copy}>{copied ? "Copied" : "Copy"}</Button>
              <Button onClick={onDone}>I have noted it</Button>
            </>}>
      <p className="form-error" role="alert">
        This password is shown once. It cannot be seen again. Give it to the crew
        member yourself. Do not send it by SMS or WhatsApp.
      </p>
      <p>Name: <strong>{issued.crew.name}</strong></p>
      <p>Login ID: <strong>{issued.login_id}</strong></p>
      <p>Password: <strong data-testid="issued-password">{issued.password}</strong></p>
    </Dialog>
  );
}

/** Jobs a change put on the Needs scheduling list (ADM-CRW-12). */
export function ReleasedJobs({ jobs }: { jobs: ReleasedJob[] }) {
  if (jobs.length === 0) return null;
  return (
    <div role="status">
      <p>{jobs.length} job{jobs.length === 1 ? "" : "s"} went to Needs scheduling.</p>
      <ul>
        {jobs.map((j) => (
          <li key={j.job_id}>{showDate(j.date)}: {j.service}, {j.registration}</li>
        ))}
      </ul>
    </div>
  );
}
