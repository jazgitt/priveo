import { useQuery } from "@tanstack/react-query";
import { useSite } from "../../site/SiteContext";
import { useState } from "react";

import { api } from "../../api/client";
import { Card, SelectField, StatusChip, Table, TextField } from "../../components";
import { dayOf, formatDate, stars } from "../support/format";
import type {
  CheckInItem, CheckInsReport, FeedbackItem, OptionAdmin, RatingItem, RatingsReport,
} from "../support/types";
import "../support/support.css";
import { OptionsManager } from "./OptionsManager";

type Tab = "feedback" | "ratings" | "checkins" | "categories";
const TABS: { id: Tab; label: string }[] = [
  { id: "feedback", label: "Feedback" },
  { id: "ratings", label: "Ratings" },
  { id: "checkins", label: "Check-ins" },
  { id: "categories", label: "Categories and tags" },
];

interface Range { society: string; from: string; to: string }

function inRange(r: Range, society: string, created: string): boolean {
  const d = dayOf(created);
  return (!r.society || society === r.society) && (!r.from || d >= r.from) && (!r.to || d <= r.to);
}

function Filters({ value, onChange }: { value: Range; onChange: (r: Range) => void }) {
  return (
    <>
      <TextField label="From" type="date" value={value.from}
                 onChange={(e) => onChange({ ...value, from: e.target.value })} />
      <TextField label="To" type="date" value={value.to}
                 onChange={(e) => onChange({ ...value, to: e.target.value })} />
    </>
  );
}

/** The date range, plus the chosen site as the society (ADM-SITE-01). */
function useRange(): [Range, (r: Range) => void] {
  const site = useSite();
  const [r, set] = useState<Range>({ society: "", from: "", to: "" });
  return [{ ...r, society: site.name }, (next) => set({ ...next, society: "" })];
}

function FeedbackTab() {
  const [category, setCategory] = useState("");
  const [rating, setRating] = useState("");
  const [range, setRange] = useRange();
  const qs = new URLSearchParams();
  if (category) qs.set("category", category);
  if (rating) qs.set("rating", rating);
  const q = qs.toString();
  const list = useQuery({
    queryKey: ["admin", "feedback", q],
    queryFn: () => api<FeedbackItem[]>(`/v1/admin/feedback${q ? `?${q}` : ""}`),
  });
  const options = useQuery({
    queryKey: ["admin", "support-options"],
    queryFn: () => api<OptionAdmin[]>("/v1/admin/support/options"),
  });
  const rows = (list.data ?? []).filter((f) => inRange(range, f.society, f.created_at));
  const cats = (options.data ?? []).filter((o) => o.kind === "feedback_category");

  return (
    <Card>
      <div className="sp-filters">
        <SelectField label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All</option>
          {cats.map((o) => <option key={o.id} value={o.name}>{o.name}</option>)}
        </SelectField>
        <SelectField label="Rating" value={rating} onChange={(e) => setRating(e.target.value)}>
          <option value="">All</option>
          {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} stars</option>)}
        </SelectField>
        <Filters value={range} onChange={setRange} />
      </div>
      {list.isLoading && <p className="muted">Loading...</p>}
      {list.isError && <p role="alert">Could not load the feedback.</p>}
      {list.data && (
        <Table<FeedbackItem> rows={rows} rowKey={(f) => f.id} empty="No feedback matches."
          columns={[
            { key: "date", header: "Date", render: (f) => formatDate(f.created_at) },
            { key: "customer", header: "Customer", render: (f) => `${f.customer_name}, ${f.society}` },
            { key: "category", header: "Category", render: (f) => f.category ?? "-" },
            { key: "rating", header: "Rating", render: (f) => stars(f.rating) },
            { key: "comment", header: "Comment", render: (f) => f.comment || "-" },
            { key: "testimonial", header: "Testimonial", render: (f) => f.testimonial_permission
              ? <StatusChip tone="ok">May quote</StatusChip> : "No" },
          ]} />
      )}
    </Card>
  );
}

function RatingsTab() {
  const [range, setRange] = useRange();
  const report = useQuery({
    queryKey: ["admin", "ratings"],
    queryFn: () => api<RatingsReport>("/v1/admin/ratings"),
  });
  const items = (report.data?.items ?? []).filter((r) => inRange(range, r.society, r.created_at));
  const tagCounts: Record<string, number> = {};
  for (const r of items) for (const t of r.tags) tagCounts[t] = (tagCounts[t] ?? 0) + 1;
  const avg = items.length ? items.reduce((s, r) => s + r.rating, 0) / items.length : null;

  return (
    <div className="sp-stack">
      <Card>
        <div className="sp-filters">
          <Filters value={range} onChange={setRange} />
        </div>
        {report.isLoading && <p className="muted">Loading...</p>}
        {report.isError && <p role="alert">Could not load the ratings.</p>}
        {report.data && (
          <p>
            <strong>{items.length}</strong> ratings, average{" "}
            <strong>{avg === null ? "-" : avg.toFixed(2)}</strong>
          </p>
        )}
      </Card>
      {report.data && (
        <>
          <Card title="Tags">
            <ul className="sp-list">
              {Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).map(([tag, n]) => (
                <li key={tag}>{tag}: {n}</li>
              ))}
              {Object.keys(tagCounts).length === 0 && <li className="muted">No tags yet.</li>}
            </ul>
          </Card>
          <Card title="Visit ratings">
            <Table<RatingItem> rows={items} rowKey={(r) => `${r.visit_id}-${r.created_at}`}
              empty="No ratings match."
              columns={[
                { key: "date", header: "Date", render: (r) => formatDate(r.created_at) },
                { key: "society", header: "Society", render: (r) => r.society },
                { key: "visit", header: "Visit", render: (r) => r.visit_id },
                { key: "rating", header: "Rating", render: (r) => stars(r.rating) },
                { key: "tags", header: "Tags", render: (r) => r.tags.join(", ") || "-" },
                { key: "comment", header: "Comment", render: (r) => r.comment || "-" },
                { key: "testimonial", header: "Testimonial", render: (r) =>
                  r.testimonial_permission ? <StatusChip tone="ok">May quote</StatusChip> : "No" },
              ]} />
          </Card>
        </>
      )}
    </div>
  );
}

function CheckInsTab() {
  const [range, setRange] = useRange();
  const report = useQuery({
    queryKey: ["admin", "checkins"],
    queryFn: () => api<CheckInsReport>("/v1/admin/checkins"),
  });
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
    <div className="sp-stack">
      <Card>
        <div className="sp-filters">
          <Filters value={range} onChange={setRange} />
        </div>
        {report.isLoading && <p className="muted">Loading...</p>}
        {report.isError && <p role="alert">Could not load the check-ins.</p>}
      </Card>
      {report.data && (
        <>
          <Card title="Average by category">
            <ul className="sp-list">
              {Object.entries(sums).map(([cat, s]) => (
                <li key={cat}>{cat}: {(s.total / s.n).toFixed(2)}</li>
              ))}
              {Object.keys(sums).length === 0 && <li className="muted">No check-ins yet.</li>}
            </ul>
          </Card>
          <Card title="Check-ins">
            <Table<CheckInItem> rows={items} rowKey={(c) => c.id} empty="No check-ins match."
              columns={[
                { key: "date", header: "Date", render: (c) => formatDate(c.created_at) },
                { key: "customer", header: "Customer", render: (c) => `${c.customer_name}, ${c.society}` },
                { key: "vehicle", header: "Vehicle", render: (c) => c.vehicle_label },
                { key: "cycle", header: "Cycle from", render: (c) => formatDate(c.cycle_start) },
                { key: "answers", header: "Ratings", render: (c) =>
                  c.answers.map((a) => `${a.category} ${a.rating}`).join(", ") },
                { key: "comment", header: "Comment", render: (c) => c.comment || "-" },
              ]} />
          </Card>
        </>
      )}
    </div>
  );
}

/** Feedback, ratings and check-ins (ADM-FDB-01 to -07). */
export function FeedbackPage() {
  const [tab, setTab] = useState<Tab>("feedback");
  return (
    <>
      <h1 className="page-title">Feedback</h1>
      <div className="sp-tabs" role="tablist" aria-label="Feedback views">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" className="sp-tab"
                  aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === "feedback" && <FeedbackTab />}
      {tab === "ratings" && <RatingsTab />}
      {tab === "checkins" && <CheckInsTab />}
      {tab === "categories" && <OptionsManager />}
    </>
  );
}
