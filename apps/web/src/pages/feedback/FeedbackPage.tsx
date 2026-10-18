import { useQuery } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { useState, type ReactNode } from "react";

import { api } from "@/api/client";
import { DataTable } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState, PageHeader, Panel, StatRow, StatTile } from "@/blocks/layout";
import { StatusBadge } from "@/blocks/status";
import { Tabs } from "@/components";
import { useSite } from "@/site/SiteContext";
import { Input } from "@/ui/input";

import { dayOf, formatDate } from "../support/format";
import type { CheckInItem, CheckInsReport, FeedbackItem, OptionAdmin, RatingItem, RatingsReport } from "../support/types";
import { OptionsManager } from "./OptionsManager";

const TABS = [
  { id: "feedback", label: "Feedback" },
  { id: "ratings", label: "Ratings" },
  { id: "checkins", label: "Check-ins" },
  { id: "categories", label: "Categories and tags" },
] as const;

interface Range { society: string; from: string; to: string }

function inRange(r: Range, society: string, created: string): boolean {
  const d = dayOf(created);
  return (!r.society || society === r.society) && (!r.from || d >= r.from) && (!r.to || d <= r.to);
}

function DateFilters({ value, onChange }: { value: Range; onChange: (r: Range) => void }) {
  return (
    <>
      <Field label="From" className="w-44">{(p) => <Input {...p} type="date" value={value.from} onChange={(e) => onChange({ ...value, from: e.target.value })} />}</Field>
      <Field label="To" className="w-44">{(p) => <Input {...p} type="date" value={value.to} onChange={(e) => onChange({ ...value, to: e.target.value })} />}</Field>
    </>
  );
}

/** The date range, plus the chosen site as the society (ADM-SITE-01). */
function useRange(): [Range, (r: Range) => void] {
  const site = useSite();
  const [r, set] = useState<Range>({ society: "", from: "", to: "" });
  return [{ ...r, society: site.name }, (next) => set({ ...next, society: "" })];
}

function Stars({ n }: { n: number | null }) {
  if (n === null) return <span className="text-muted-foreground">-</span>;
  return (
    <span className="inline-flex items-center gap-1 tabular-nums" aria-label={`${n} / 5`}>
      <Star className="size-3.5 fill-gold text-gold" aria-hidden />{n}<span className="text-muted-foreground">/5</span>
    </span>
  );
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return <StatTile label={label} value={value} />;
}

const quote = (ok: boolean) => (ok ? <StatusBadge status="May quote" tone="ok" /> : <span className="text-muted-foreground">No</span>);

function FeedbackTab() {
  const [category, setCategory] = useState("");
  const [rating, setRating] = useState("");
  const [range, setRange] = useRange();
  const qs = new URLSearchParams();
  if (category) qs.set("category", category);
  if (rating) qs.set("rating", rating);
  const q = qs.toString();
  const list = useQuery({ queryKey: ["admin", "feedback", q], queryFn: () => api<FeedbackItem[]>(`/v1/admin/feedback${q ? `?${q}` : ""}`) });
  const options = useQuery({ queryKey: ["admin", "support-options"], queryFn: () => api<OptionAdmin[]>("/v1/admin/support/options") });
  const rows = list.data?.filter((f) => inRange(range, f.society, f.created_at));
  // The tiles count all feedback of the site and dates, whatever the category and rating filters say.
  const every = useQuery({ queryKey: ["admin", "feedback", ""], queryFn: () => api<FeedbackItem[]>("/v1/admin/feedback") });
  const counted = every.data?.filter((f) => inRange(range, f.society, f.created_at));
  const rated = counted?.filter((f) => f.rating !== null) ?? [];
  const average = rated.length ? rated.reduce((t, f) => t + (f.rating ?? 0), 0) / rated.length : null;
  const cats = (options.data ?? []).filter((o) => o.kind === "feedback_category");

  return (
    <>
      {list.isError && <div className="mb-4"><ErrorState message="Could not load the feedback." /></div>}
      <StatRow label="Feedback summary">
        <StatTile label="Total feedback" value={counted?.length} loading={every.isPending}
                  selected={!rating && !category} onSelect={() => { setRating(""); setCategory(""); }} />
        <StatTile label="Average rating" value={average === null ? "-" : average.toFixed(2)} loading={every.isPending}
                  hint={`${rated.length} rated`} />
        {[5, 4, 3, 2, 1].map((n) => (
          <StatTile key={n} label={`${n} ${n === 1 ? "star" : "stars"}`} value={rated.filter((f) => f.rating === n).length}
                    loading={every.isPending} selected={rating === String(n)}
                    onSelect={() => setRating(rating === String(n) ? "" : String(n))} />
        ))}
        <StatTile label="May be quoted" value={counted?.filter((f) => f.testimonial_permission).length} loading={every.isPending} />
      </StatRow>
      <DataTable<FeedbackItem>
        rows={rows}
        loading={list.isLoading}
        rowKey={(f) => f.id}
        toolbar={(
          <div className="flex flex-wrap items-end gap-3">
            <Field label="Category" className="w-52">
              {(p) => <SelectBox {...p} value={category || NONE} onChange={(v) => setCategory(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All" }, ...cats.map((o) => ({ value: o.name, label: o.name }))]} />}
            </Field>
            <Field label="Rating" className="w-36">
              {(p) => <SelectBox {...p} value={rating || NONE} onChange={(v) => setRating(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All" }, ...[5, 4, 3, 2, 1].map((n) => ({ value: String(n), label: `${n} stars` }))]} />}
            </Field>
            <DateFilters value={range} onChange={setRange} />
          </div>
        )}
        empty={<EmptyState title="No feedback matches" />}
        columns={[
          { key: "date", header: "Date", width: "7rem", cell: (f) => formatDate(f.created_at) },
          { key: "customer", header: "Customer", width: "16%", cell: (f) => f.customer_name },
          { key: "category", header: "Category", width: "11rem", cell: (f) => f.category ?? "-" },
          { key: "rating", header: "Rating", width: "6rem", cell: (f) => <Stars n={f.rating} /> },
          { key: "comment", header: "Comment", wrap: true, cell: (f) => f.comment || <span className="text-muted-foreground">-</span> },
          { key: "testimonial", header: "Testimonial", width: "8rem", cell: (f) => quote(f.testimonial_permission) },
        ]}
      />
    </>
  );
}

function RatingsTab() {
  const [range, setRange] = useRange();
  const report = useQuery({ queryKey: ["admin", "ratings"], queryFn: () => api<RatingsReport>("/v1/admin/ratings") });
  const items = (report.data?.items ?? []).filter((r) => inRange(range, r.society, r.created_at));
  const tagCounts: Record<string, number> = {};
  for (const r of items) for (const t of r.tags) tagCounts[t] = (tagCounts[t] ?? 0) + 1;
  const avg = items.length ? items.reduce((s, r) => s + r.rating, 0) / items.length : null;
  const tags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end gap-3"><DateFilters value={range} onChange={setRange} /></div>
      {report.isError && <ErrorState message="Could not load the ratings." />}
      {report.data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Stat label="Ratings" value={items.length} />
            <Stat label="Average" value={avg === null ? "-" : avg.toFixed(2)} />
            <Stat label="May be quoted" value={items.filter((r) => r.testimonial_permission).length} />
          </div>
          <Panel title="Tags" description="How often customers chose each tag. Ratings are for the visit, not a crew member.">
            {tags.length === 0 ? <p className="m-0 text-sm text-muted-foreground">No tags yet.</p> : (
              <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                {tags.map(([tag, n]) => (
                  <li key={tag} className="inline-flex items-center gap-2 rounded-full border bg-muted/50 py-1 pr-1 pl-3 text-sm">
                    <span>{tag}</span><span className="rounded-full bg-card px-2 text-xs font-semibold tabular-nums" aria-label={`${tag}: ${n}`}>{n}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </>
      )}
      <DataTable<RatingItem>
        rows={report.data ? items : undefined}
        loading={report.isLoading}
        rowKey={(r) => `${r.visit_id}-${r.created_at}`}
        empty={<EmptyState title="No ratings match" />}
        columns={[
          { key: "date", header: "Date", width: "7rem", cell: (r) => formatDate(r.created_at) },
          { key: "rating", header: "Rating", width: "6rem", cell: (r) => <Stars n={r.rating} /> },
          { key: "tags", header: "Tags", width: "22%", wrap: true, cell: (r) => r.tags.join(", ") || "-" },
          { key: "comment", header: "Comment", wrap: true, cell: (r) => r.comment || <span className="text-muted-foreground">-</span> },
          { key: "testimonial", header: "Testimonial", width: "8rem", cell: (r) => quote(r.testimonial_permission) },
        ]}
      />
    </div>
  );
}

function CheckInsTab() {
  const [range, setRange] = useRange();
  const report = useQuery({ queryKey: ["admin", "checkins"], queryFn: () => api<CheckInsReport>("/v1/admin/checkins") });
  const items = (report.data?.items ?? []).filter((c) => inRange(range, c.society, c.created_at));
  const sums: Record<string, { total: number; n: number }> = {};
  for (const c of items) {
    for (const a of c.answers) {
      const s = (sums[a.category] ??= { total: 0, n: 0 });
      s.total += a.rating;
      s.n += 1;
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end gap-3"><DateFilters value={range} onChange={setRange} /></div>
      {report.isError && <ErrorState message="Could not load the check-ins." />}
      {report.data && (Object.keys(sums).length === 0
        ? <p className="m-0 text-sm text-muted-foreground">No check-ins yet.</p>
        : (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {Object.entries(sums).map(([cat, s]) => <Stat key={cat} label={cat} value={<span aria-label={`${cat}: ${(s.total / s.n).toFixed(2)}`}>{(s.total / s.n).toFixed(2)}</span>} />)}
          </div>
        ))}
      <DataTable<CheckInItem>
        rows={report.data ? items : undefined}
        loading={report.isLoading}
        rowKey={(c) => c.id}
        empty={<EmptyState title="No check-ins match" />}
        columns={[
          { key: "date", header: "Date", width: "7rem", cell: (c) => formatDate(c.created_at) },
          { key: "customer", header: "Customer", width: "15%", cell: (c) => c.customer_name },
          { key: "vehicle", header: "Vehicle", width: "12%", cell: (c) => c.vehicle_label },
          { key: "cycle", header: "Cycle from", width: "7rem", cell: (c) => formatDate(c.cycle_start) },
          { key: "answers", header: "Ratings", width: "26%", wrap: true, cell: (c) => c.answers.map((a) => `${a.category} ${a.rating}`).join(", ") },
          { key: "comment", header: "Comment", wrap: true, cell: (c) => c.comment || <span className="text-muted-foreground">-</span> },
        ]}
      />
    </div>
  );
}

/** Feedback, ratings and check-ins (ADM-FDB-01 to -07). */
export function FeedbackPage() {
  const site = useSite();
  const [tab, setTab] = useState<string>("feedback");
  return (
    <>
      <PageHeader title="Feedback" site={site.name || undefined} description="What customers say: feedback, visit ratings and monthly check-ins." />
      <Tabs tabs={TABS} active={tab} label="Feedback views" onChange={setTab}>
        {tab === "feedback" && <FeedbackTab />}
        {tab === "ratings" && <RatingsTab />}
        {tab === "checkins" && <CheckInsTab />}
        {tab === "categories" && <OptionsManager />}
      </Tabs>
    </>
  );
}
