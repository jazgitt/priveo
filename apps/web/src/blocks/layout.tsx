import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** The top of every page: title, what it is for, the site, and the main actions. */
export function PageHeader({ title, description, site, actions, back }: {
  title: ReactNode;
  description?: ReactNode;
  /** The site the page shows (ADM-SITE-01). */
  site?: string;
  actions?: ReactNode;
  back?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {back && <div className="mb-2 text-sm">{back}</div>}
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {(description || site) && (
          <p className="mt-1 text-sm text-muted-foreground">
            {site && <span className="font-medium text-foreground">{site}</span>}
            {site && description && <span aria-hidden> · </span>}
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

/** A titled panel. `actions` sit at the right of the title. */
export function Panel({ title, description, actions, children, className, bodyClassName }: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("overflow-hidden rounded-xl border bg-card shadow-xs", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b px-5 py-3.5">
          <div className="min-w-0">
            {title && <h2 className="text-[0.9375rem] font-semibold">{title}</h2>}
            {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={cn("p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

export interface DetailItem {
  label: string;
  value: ReactNode;
  /** Takes the whole row. */
  wide?: boolean;
}

/** Labels and values in a grid, instead of sentences joined with "·". */
export function DetailList({ items, columns = 2, className }: {
  items: DetailItem[];
  columns?: 1 | 2 | 3 | 4;
  className?: string;
}) {
  const cols = { 1: "sm:grid-cols-1", 2: "sm:grid-cols-2", 3: "sm:grid-cols-3", 4: "sm:grid-cols-4" }[columns];
  return (
    <dl className={cn("grid grid-cols-1 gap-x-6 gap-y-3", cols, className)}>
      {items.map((it) => (
        <div key={it.label} className={cn("min-w-0", it.wide && "sm:col-span-full")}>
          <dt className="text-xs font-medium text-muted-foreground">{it.label}</dt>
          <dd className="mt-0.5 break-words">{isEmpty(it.value) ? "-" : it.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function isEmpty(v: ReactNode): boolean {
  return v === null || v === undefined || v === "" || v === false;
}

/** What to show when a list has nothing, and what to do about it. */
export function EmptyState({ title, children, action }: {
  title: string; children?: ReactNode; action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center">
      <p className="font-medium">{title}</p>
      {children && <p className="max-w-md text-sm text-muted-foreground">{children}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

/** An error from the API, shown in place of the content it stopped. */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="font-medium underline underline-offset-4" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
