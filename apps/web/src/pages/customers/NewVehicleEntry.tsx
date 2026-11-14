import { useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";

import { api, ApiError } from "@/api/client";
import { Field } from "@/blocks/fields";
import { useAppMutation } from "@/blocks/mutation";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import type { Catalogue } from "./api";

/**
 * Add a make, model or variant that is not in the list yet. It is saved to the
 * vehicle catalogue (the same one as Reference data > Vehicles), so it stays for
 * every later customer. Not a form: it sits inside the wizard's own form.
 */
export function NewVehicleEntry({ initial, makes, categories, onAdded }: {
  initial: { make: string; model: string };
  makes: string[];
  categories: string[];
  onAdded: (entry: Catalogue) => void;
}) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [variant, setVariant] = useState("");
  const [category, setCategory] = useState("");
  const save = useAppMutation<void, Catalogue>({
    mutationFn: () => api<Catalogue>("/v1/admin/directory/vehicle-catalogue", {
      method: "POST", body: { make: make.trim(), model: model.trim(), variant: variant.trim(), category: category.trim() },
    }),
    pending: "Adding to the vehicle list…",
    success: "Added to the vehicle list.",
    onSuccess: (entry) => {
      // Put it in the list at once, so the dropdowns can show it before the refresh ends.
      qc.setQueryData<Catalogue[]>(["customer-catalogue"], (old) => [...(old ?? []), entry]);
      onAdded(entry);
      setOpen(false); setVariant("");
    },
    invalidate: [["customer-catalogue"]],
  });
  const fe = (f: string) => (save.error instanceof ApiError ? save.error.fields[f] : undefined);
  const noEnter = (e: React.KeyboardEvent) => { if (e.key === "Enter") e.preventDefault(); };

  if (!open) {
    return (
      <div className="sm:col-span-3">
        <Button type="button" variant="outline" size="sm"
                onClick={() => { setMake(initial.make); setModel(initial.model); setOpen(true); }}>
          <Plus aria-hidden /> Make, model or variant not in the list? Add it
        </Button>
      </div>
    );
  }
  return (
    <div role="group" aria-label="Add a new vehicle to the list" onKeyDown={noEnter}
         className="grid grid-cols-1 gap-4 rounded-lg border bg-muted/40 p-4 sm:col-span-3 sm:grid-cols-2">
      <p className="m-0 text-sm font-medium sm:col-span-2">Add a vehicle to the list</p>
      <Field label="New make" error={fe("make")} hint="Keep the existing make to add only a model.">
        {(p) => <Input {...p} maxLength={60} list="new-vehicle-makes" value={make} onChange={(e) => setMake(e.target.value)} />}
      </Field>
      <Field label="New model" error={fe("model")}>
        {(p) => <Input {...p} maxLength={80} value={model} onChange={(e) => setModel(e.target.value)} />}
      </Field>
      <Field label="New variant" optional error={fe("variant")}>
        {(p) => <Input {...p} maxLength={80} value={variant} onChange={(e) => setVariant(e.target.value)} />}
      </Field>
      <Field label="New vehicle category" error={fe("category")} hint="Pick one in use or type a new one.">
        {(p) => <Input {...p} maxLength={40} list="new-vehicle-categories" value={category} onChange={(e) => setCategory(e.target.value)} />}
      </Field>
      <datalist id="new-vehicle-categories">{categories.map((c) => <option key={c} value={c} />)}</datalist>
      <datalist id="new-vehicle-makes">{makes.map((c) => <option key={c} value={c} />)}</datalist>
      <div className="flex justify-end gap-2 sm:col-span-2">
        <Button type="button" variant="ghost" disabled={save.isPending} onClick={() => setOpen(false)}>Cancel</Button>
        <Button type="button" disabled={save.isPending || !make.trim() || !model.trim() || !category.trim()} onClick={() => save.mutate()}>
          Save to list
        </Button>
      </div>
    </div>
  );
}
