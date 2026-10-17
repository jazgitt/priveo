import { EmptyState, PageHeader } from "../blocks/layout";
import type { NavItem } from "../nav";

/** An area whose screens are not built yet. */
export function Placeholder({ item }: { item: NavItem }) {
  return (
    <>
      <PageHeader title={item.label} description={item.about} />
      <EmptyState title="Not built yet">This area is not built yet.</EmptyState>
    </>
  );
}
