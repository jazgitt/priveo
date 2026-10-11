import { Link, useParams } from "react-router-dom";

import { ApiErrorNote } from "../../components/ApiErrorNote";
import { StatusChip } from "../../components";
import { useCrew } from "./api";
import {
  AccountPanel, DetailsPanel, ExceptionsPanel, HoursPanel, RolePanel, SessionsPanel,
} from "./panels";

export function CrewDetailPage() {
  const { id = "" } = useParams();
  const q = useCrew(id);
  if (q.isPending) return <p className="loading">Loading...</p>;
  if (q.isError) {
    return (
      <>
        <p><Link className="sp-link" to="/crew">Back to crew</Link></p>
        <ApiErrorNote error={q.error} />
      </>
    );
  }
  const c = q.data;
  // The key resets each panel's form when the saved record changes.
  const v = JSON.stringify([c.name, c.mobile, c.role, c.paired_member_id, c.working_hours]);
  return (
    <>
      <p><Link className="sp-link" to="/crew">Back to crew</Link></p>
      <h1 className="page-title">{c.name}</h1>
      <p>
        <StatusChip tone={c.active ? "ok" : "neutral"}>{c.active ? "Active" : "Inactive"}</StatusChip>{" "}
        {c.locked && <StatusChip tone="warn">Locked</StatusChip>}{" "}
        {c.role}, {c.society}, {c.mobile}
      </p>
      <DetailsPanel key={`d-${v}`} crew={c} />
      <RolePanel key={`r-${v}`} crew={c} />
      <HoursPanel key={`h-${v}`} crew={c} />
      <ExceptionsPanel crew={c} />
      <AccountPanel crew={c} />
      <SessionsPanel crew={c} />
    </>
  );
}
