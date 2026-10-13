import { Card } from "../components";
import type { NavItem } from "../nav";

/** An area whose screens are not built yet. */
export function Placeholder({ item }: { item: NavItem }) {
  return (
    <>
      <h1 className="page-title">{item.label}</h1>
      <Card>
        <p>{item.about}</p>
        <p className="muted">This area is not built yet.</p>
      </Card>
    </>
  );
}
