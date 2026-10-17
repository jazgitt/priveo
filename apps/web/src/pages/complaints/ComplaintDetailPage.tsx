import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { BusyButton } from "@/blocks/FormDialog";
import { DetailList, ErrorState, PageHeader, Panel } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { showDateTime } from "@/components/format";
import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { Skeleton } from "@/ui/skeleton";
import { Textarea } from "@/ui/textarea";

import { formatDate } from "../support/format";
import { KEYS } from "../support/hooks";
import type { ComplaintDetail } from "../support/types";
import { STATUSES, statusTone } from "./ComplaintsPage";

interface LinkedVisit {
  status: string; date: string;
  jobs: { id: string; service: string; crew_name: string;
    checklist: { key: string; label: string; checked_at: string | null }[];
    proof: { id: string; kind: string; url: string }[] }[];
}

/** One complaint: the thread, the status and a note box (ADM-CMP-02 to -04, -06, -07). */
export function ComplaintDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");
  const path = `/v1/admin/complaints/${id}`;

  const detail = useQuery({ queryKey: [...KEYS.complaints, id], queryFn: () => api<ComplaintDetail>(path) });
  const visit = useQuery({ queryKey: ["complaint-visit", id, detail.data?.visit_id], enabled: !!detail.data?.visit_id,
    queryFn: () => api<LinkedVisit>(`${path}/visit`) });

  const save = useAppMutation<{ kind: "status" | "note"; status?: string; note: string }, ComplaintDetail>({
    mutationFn: (v) => api(`${path}/${v.kind === "status" ? "status" : "notes"}`, {
      method: "POST", body: v.kind === "status" ? { status: v.status, note: v.note } : { note: v.note },
    }),
    success: (_d, v) => (v.kind === "status" ? `Status is now ${v.status}.` : "Note added."),
    onSuccess: (data) => {
      qc.setQueryData([...KEYS.complaints, id], data);
      void qc.invalidateQueries({ queryKey: KEYS.complaints });
      setNote("");
      setStatus("");
    },
  });

  const back = <Link to="/complaints" className="inline-flex items-center gap-1 text-muted-foreground"><ChevronLeft className="size-4" aria-hidden />Back to complaints</Link>;
  if (detail.isLoading) return <><PageHeader title="Complaint" back={back} /><Skeleton className="h-64 w-full" /></>;
  if (detail.isError || !detail.data) return <><PageHeader title="Complaint" back={back} /><ErrorState message="Could not load this complaint." onRetry={() => void detail.refetch()} /></>;
  const c = detail.data;

  const submit = async () => {
    if (status) {
      if (await confirm({
        title: `Set ${c.display_id} to ${status}?`,
        description: note.trim() ? "The customer sees the new status and your note." : "The customer sees the new status.",
        confirmLabel: "Change status",
      })) save.mutate({ kind: "status", status, note: note.trim() });
    } else if (note.trim()) save.mutate({ kind: "note", note: note.trim() });
  };

  return (
    <>
      <PageHeader back={back}
                  title={<span className="flex flex-wrap items-center gap-3">{c.display_id}
                    <StatusBadge status={c.status} tone={statusTone(c.status)} />
                    {c.overdue && <StatusBadge status="Overdue" tone="error" />}</span>}
                  description={<>{c.category} · raised {formatDate(c.created_at)}</>} />
      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex min-w-0 flex-col gap-6">
          <Panel title="Complaint">
            <p className="mt-0 mb-4 text-[0.9375rem] whitespace-pre-wrap">{c.description}</p>
            <DetailList columns={3} items={[
              { label: "Customer", value: c.customer_name },
              { label: "Flat", value: c.flat },
              { label: "Society", value: c.society },
              { label: "Vehicle", value: c.vehicle || "No vehicle linked" },
              { label: "Photos", value: c.photo_keys.length > 0 ? `${c.photo_keys.length} attached` : "None" },
            ]} />
            {(c.photo_urls ?? []).length > 0 && (
              <div className="mt-4 flex flex-wrap gap-3">
                {(c.photo_urls ?? []).map((url, i) => (
                  <a key={url} href={url} target="_blank" rel="noreferrer">
                    <img src={url} alt={`Complaint photo ${i + 1}`} className="h-32 w-44 rounded-lg border object-cover" />
                  </a>
                ))}
              </div>
            )}
          </Panel>

          {c.visit_id && (
            <Panel title="Linked visit">
              <section aria-label="Linked visit">
                {visit.isPending && <Skeleton className="h-24" />}
                {visit.isError && <ErrorState message="Could not load visit proof." onRetry={() => void visit.refetch()} />}
                {visit.data && (
                  <div className="flex flex-col gap-4">
                    <p className="m-0 flex items-center gap-2 text-sm">{formatDate(visit.data.date)} <StatusBadge status={visit.data.status} /></p>
                    {visit.data.jobs.map((j) => (
                      <div key={j.id} className="rounded-lg border p-4">
                        <h4 className="m-0 mb-2 text-sm font-semibold">{j.service} <span className="font-normal text-muted-foreground">· {j.crew_name}</span></h4>
                        <ul className="m-0 grid list-none grid-cols-1 gap-1 p-0 text-sm sm:grid-cols-2">
                          {j.checklist.map((item) => (
                            <li key={item.key} className={cn(!item.checked_at && "text-muted-foreground")}>
                              {item.checked_at ? "✓" : "○"} {item.label} · {item.checked_at ? formatDate(item.checked_at) : "Not checked"}
                            </li>
                          ))}
                        </ul>
                        {j.proof.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-3">
                            {j.proof.map((p) => (p.kind === "video"
                              ? <video key={p.id} src={p.url} controls preload="metadata" className="h-32 rounded-lg border" />
                              : <a key={p.id} href={p.url} target="_blank" rel="noreferrer"><img src={p.url} alt="Linked visit proof" className="h-32 w-44 rounded-lg border object-cover" /></a>))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </Panel>
          )}

          <Panel title="Thread">
            {c.updates.length === 0 && <p className="m-0 text-sm text-muted-foreground">No updates yet.</p>}
            <ol className="m-0 flex list-none flex-col gap-3 p-0">
              {c.updates.map((u) => (
                <li key={u.id} className={cn("max-w-[85%] rounded-xl border px-4 py-2.5 text-sm",
                  u.author_role === "admin" ? "self-end border-gold/30 bg-gold/10" : "self-start bg-muted/50")}>
                  <p className="m-0 text-xs text-muted-foreground">
                    {u.author_role === "admin" ? "Admin" : "Customer"} · {showDateTime(u.created_at)}{u.status ? ` · status ${u.status}` : ""}
                  </p>
                  <p className="m-0 mt-0.5 whitespace-pre-wrap">{u.note}</p>
                </li>
              ))}
            </ol>
          </Panel>
        </div>

        <Panel title="Update" description="Notes and status changes are shown to the customer." className="xl:sticky xl:top-20">
          <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
            <Field label="Set status">
              {(p) => <SelectBox {...p} value={status || NONE} onChange={(v) => setStatus(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: `Keep ${c.status}` }, ...STATUSES.filter((s) => s !== c.status).map((s) => ({ value: s, label: s }))]} />}
            </Field>
            <Field label="Note for the customer" hint={`${note.length}/1000`}>
              {(p) => <Textarea {...p} rows={5} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />}
            </Field>
            <BusyButton type="submit" busy={save.isPending} disabled={!status && !note.trim()}>
              {status ? "Change status" : "Add note"}
            </BusyButton>
            {(status || note) && <Button type="button" variant="ghost" onClick={() => { setStatus(""); setNote(""); }}>Clear</Button>}
          </form>
        </Panel>
      </div>
    </>
  );
}
