import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { ErrorState } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { Button } from "@/ui/button";
import { Skeleton } from "@/ui/skeleton";

import type { Crew } from "../api";
import type { CrewRulesSection } from ".";

/** HomeZoneOut: the zone in force and the zones of the cleaner's society. */
interface HomeZone {
  home_zone_id: string | null;
  follows_member: string | null;
  editable: boolean;
  zones: { id: string; name: string }[];
}

function ZoneForm({ crewId, data }: { crewId: string; data: HomeZone }) {
  const [zone, setZone] = useState(data.home_zone_id ?? NONE);
  const save = useAppMutation<{ home_zone_id: string | null }, HomeZone>({
    mutationFn: (body) => api<HomeZone>(`/v1/admin/crew/${crewId}/home-zone`, { method: "PUT", body }),
    success: "Home zone saved.",
    invalidate: [["crew", crewId, "home-zone"]],
  });
  const choices = [{ value: NONE, label: "No home zone" }, ...data.zones.map((z) => ({ value: z.id, label: z.name }))];
  const changed = zone !== (data.home_zone_id ?? NONE);
  const hint = data.follows_member
    ? `A Trainee follows ${data.follows_member}'s home zone. Change it on the Member.`
    : "The planner fills this zone first. Several cleaners may share a zone.";

  return (
    <div className="flex flex-col gap-4">
      <Field label="Home zone" hint={hint}>
        {(p) => (
          <SelectBox {...p} aria-label="Home zone" className="w-56" value={zone} onChange={setZone}
            choices={choices} disabled={!data.editable} />
        )}
      </Field>
      {data.editable && (
        <div>
          <Button type="button" disabled={!changed || save.isPending}
            onClick={() => save.mutate({ home_zone_id: zone === NONE ? null : zone })}>
            Save
          </Button>
        </div>
      )}
    </div>
  );
}

/** SCHS-29: one home zone for each Member or Manager. A Trainee shows the Member's. */
export function HomeZoneSection({ crew }: { crew: Crew }) {
  const q = useQuery({
    queryKey: ["crew", crew.id, "home-zone"],
    queryFn: () => api<HomeZone>(`/v1/admin/crew/${crew.id}/home-zone`),
  });
  if (q.isError) return <ErrorState message="The home zone could not be loaded." onRetry={() => void q.refetch()} />;
  if (!q.data) return <Skeleton className="h-16 w-full" />;
  return <ZoneForm key={JSON.stringify(q.data)} crewId={crew.id} data={q.data} />;
}

export const section: CrewRulesSection = {
  id: "home-zone", title: "Home zone", order: 20, component: HomeZoneSection,
};
