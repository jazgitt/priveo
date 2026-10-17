import { useId, type ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Label } from "@/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/ui/select";

export interface ControlProps {
  id: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}

/**
 * A label, a control, and a hint or an error under it. The control is given
 * through `children(props)` so it gets the id and the aria links.
 */
export function Field({ label, hint, error, className, children, optional }: {
  label: string;
  hint?: ReactNode;
  error?: string;
  optional?: boolean;
  className?: string;
  children: (p: ControlProps) => ReactNode;
}) {
  const id = useId();
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      {/* "(optional)" sits beside the label, so the field's name is just the label. */}
      <span className="flex items-baseline gap-1">
        <Label htmlFor={id} className="text-[0.8125rem]">{label}</Label>
        {optional && <span className="text-[0.8125rem] text-muted-foreground">(optional)</span>}
      </span>
      {children({ id, "aria-invalid": error ? true : undefined, "aria-describedby": describedBy })}
      {hint && !error && <p id={`${id}-hint`} className="text-xs text-muted-foreground">{hint}</p>}
      {error && <p id={`${id}-err`} role="alert" className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

export interface Choice { value: string; label: ReactNode; disabled?: boolean }

/**
 * A dropdown. `value` "" shows the placeholder. Choices must not use "" as a
 * value; use NONE for an explicit "None" choice.
 */
export function SelectBox({ value, onChange, choices, placeholder = "Choose", className, disabled, ...aria }: {
  value: string;
  onChange: (value: string) => void;
  choices: Choice[];
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  id?: string;
  "aria-label"?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}) {
  return (
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger className={cn("w-full bg-card", className)} {...aria}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent position="popper" className="max-h-72">
        {choices.map((c) => (
          <SelectItem key={c.value} value={c.value} disabled={c.disabled}>{c.label}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/** The value of an explicit "None" choice in a SelectBox. */
export const NONE = "__none";
