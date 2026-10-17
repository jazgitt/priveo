import { useQuery } from "@tanstack/react-query";
import { Search, X } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import { Field, SelectBox } from "@/blocks/fields";
import { cn } from "@/lib/utils";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { useDebounced, type Customer, type CustomerRow, type Vehicle } from "./api";

export interface PickedCustomer { id: string; name: string }

/**
 * Find a customer by name, mobile, registration or society, instead of
 * typing an ID. The results are those of the chosen site.
 */
export function CustomerPicker({ value, onChange, label = "Customer", compact = false }: {
  value: PickedCustomer | null; onChange: (c: PickedCustomer | null) => void; label?: string;
  /** No hint line under the box, for a row of filters. */
  compact?: boolean;
}) {
  const site = useSite();
  const [text, setText] = useState("");
  const q = useDebounced(text.trim(), 250);
  const results = useQuery({
    queryKey: ["customers", "pick", q, site.id],
    enabled: !value && q.length > 0,
    queryFn: () => api<CustomerRow[]>(`/v1/admin/customers?q=${encodeURIComponent(q)}${site.id ? `&society_id=${site.id}` : ""}&limit=8`),
  });

  if (value) {
    return (
      <Field label={label}>
        {(p) => (
          <div id={p.id} className="flex h-9 items-center justify-between gap-2 rounded-md border bg-muted/50 pr-1 pl-3 text-sm">
            <span className="truncate font-medium">{value.name}</span>
            <Button type="button" size="icon-sm" variant="ghost" aria-label={`Change ${label.toLowerCase()}`}
                    onClick={() => { onChange(null); setText(""); }}><X /></Button>
          </div>
        )}
      </Field>
    );
  }
  return (
    <Field label={label} hint={q && results.data?.length === 0 ? "No customer matches." : compact ? undefined : "Name, mobile, registration or society."}>
      {(p) => (
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input {...p} className="bg-card pl-9" placeholder="Search customers" value={text}
                 role="combobox" aria-expanded={(results.data?.length ?? 0) > 0} aria-controls={`${p.id}-list`}
                 onChange={(e) => setText(e.target.value)} />
          {(results.data?.length ?? 0) > 0 && (
            <ul id={`${p.id}-list`} role="listbox" aria-label={`${label} results`}
                className="absolute top-full right-0 left-0 z-50 m-0 mt-1 max-h-64 list-none overflow-y-auto rounded-md border bg-popover p-1 shadow-md">
              {results.data!.map((c) => (
                <li key={c.id} role="option" aria-selected={false} tabIndex={0}
                    className={cn("flex cursor-pointer flex-col rounded-sm px-2 py-1.5 text-sm hover:bg-accent focus:bg-accent focus:outline-none")}
                    onClick={() => onChange({ id: c.id, name: c.name })}
                    onKeyDown={(e) => { if (e.key === "Enter") onChange({ id: c.id, name: c.name }); }}>
                  <span className="font-medium">{c.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {c.mobile}{c.vehicles?.length ? ` · ${c.vehicles.map((v) => v.registration).filter(Boolean).join(", ")}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Field>
  );
}

/** The chosen customer's vehicles, filtered by `allow`. */
export function VehiclePicker({ customerId, value, onChange, allow = () => true, describe, label = "Vehicle", emptyText = "Choose a customer first" }: {
  customerId: string | null; value: string; onChange: (id: string, v: Vehicle | undefined) => void;
  allow?: (v: Vehicle) => boolean; describe?: (v: Vehicle) => string; label?: string;
  /** What the box says before a customer is chosen. */
  emptyText?: string;
}) {
  const customer = useQuery({
    queryKey: ["customer", customerId], enabled: !!customerId,
    queryFn: () => api<Customer>(`/v1/admin/customers/${customerId}`),
  });
  const vehicles = (customer.data?.vehicles ?? []).filter(allow);
  return (
    <Field label={label} hint={customerId && customer.data && vehicles.length === 0 ? "This customer has no vehicle that fits." : undefined}>
      {(p) => (
        <SelectBox {...p} value={value} disabled={!customerId} placeholder={customerId ? "Choose a vehicle" : emptyText}
                   onChange={(id) => onChange(id, vehicles.find((v) => v.id === id))}
                   choices={vehicles.map((v) => ({ value: v.id, label: describe ? describe(v) : `${v.registration || "No registration"} · ${v.make} ${v.model}` }))} />
      )}
    </Field>
  );
}
