import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";

interface Shared {
  label: string;
  error?: string;
  hint?: string;
}

function Wrap({ id, label, error, hint, children }: Shared & { id: string; children: ReactNode }) {
  return (
    <div className={`field${error ? " field-error" : ""}`}>
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && !error && <p className="field-hint" id={`${id}-hint`}>{hint}</p>}
      {error && <p className="field-msg" id={`${id}-err`} role="alert">{error}</p>}
    </div>
  );
}

export function TextField({ label, error, hint, ...rest }:
    Shared & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <Wrap id={id} label={label} error={error} hint={hint}>
      <input id={id} aria-invalid={error ? true : undefined}
             aria-describedby={error ? `${id}-err` : hint ? `${id}-hint` : undefined}
             {...rest} />
    </Wrap>
  );
}

export function SelectField({ label, error, hint, children, ...rest }:
    Shared & SelectHTMLAttributes<HTMLSelectElement>) {
  const id = useId();
  return (
    <Wrap id={id} label={label} error={error} hint={hint}>
      <select id={id} aria-invalid={error ? true : undefined} {...rest}>{children}</select>
    </Wrap>
  );
}
