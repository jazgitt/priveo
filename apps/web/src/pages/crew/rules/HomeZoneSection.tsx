import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { ErrorState } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { Button } from "@/ui/button";
import { Checkbox } from "@/ui/checkbox";
import { Skeleton } from "@/ui/skeleton";

import type { Crew } from "../api";
import type { CrewRulesSection } from ".";

export interface ZoneChoice { id: string; name: string }

/** HomeZoneOut: the zones in force and the zones of the cleaner's society. */
interface HomeZone {
  home_zone_ids: string[];
  follows_member: string | null;
  editable: boolean;
  zones: ZoneChoice[];
}

/** The same zones in the same order, for comparing a picked list with the saved one. */
export const sameZones = (a: string[], b: string[]) => a.length === b.length && [...a].sort().join() === [...b].sort().join();

/** The hint under the zone list. A Trainee follows the Member's zones. */
export const homeZoneHint = (followsMember: string | null) => (followsMember
  ? `A Trainee follows ${followsMember}'s home zones. Change them on the Member.`
  : "The planner fills these zones first. Several cleaners may share a zone.");

/**
 * A list of check boxes, one for each zone of the society. Used on an existing crew and when a
 * crew is onboarded. The caller gives the legend (the fieldset) around it.
 */
export function HomeZonePicker({ zones, value, onChange, disabled }: {
  zones: ZoneChoice[]; value: string[]; onChange: (ids: string[]) => void; disabled?: boolean;
}) {
  if (!zones.length) return <p className="m-0 text-sm text-muted-foreground">This society has no zones yet. Add zones in Site Setup.</p>;
  const toggle = (id: string) => onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id]);
  return (
    <div className="flex flex-col gap-2">
      {zones.map((z) => (
        <label key={z.id} className="flex items-center gap-2 text-sm">
          <Checkbox checked={value.includes(z.id)} disabled={disabled} onCheckedChange={() => toggle(z.id)} />
          <span>{z.name}</span>
        </label>
      ))}
    </div>
  );
}

function ZoneForm({ crewId, data }: { crewId: string; data: HomeZone }) {
  const [picked, setPicked] = useState<string[]>(data.home_zone_ids);
  const save = useAppMutation<{ home_zone_ids: string[] }, HomeZone>({
    mutationFn: (body) => api<HomeZone>(`/v1/admin/crew/${crewId}/home-zone`, { method: "PUT", body }),
    success: "Home zones saved.",
    invalidate: [["crew", crewId, "home-zone"]],
  });
  const changed = !sameZones(picked, data.home_zone_ids);

  return (
    <div className="flex flex-col gap-4">
      <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
        <legend className="mb-1.5 text-[0.8125rem] font-medium">Home zones</legend>
        <HomeZonePicker zones={data.zones} value={picked} onChange={setPicked} disabled={!data.editable} />
        <p className="m-0 text-xs text-muted-foreground">{homeZoneHint(data.follows_member)}</p>
      </fieldset>
      {data.editable && (
        <div>
          <Button type="button" disabled={!changed || save.isPending}
            onClick={() => save.mutate({ home_zone_ids: picked })}>
            Save
          </Button>
        </div>
      )}
    </div>
  );
}

/** SCHS-29: home zones for each Member or Manager (several allowed). A Trainee shows the Member's. */
export function HomeZoneSection({ crew }: { crew: Crew }) {
  const q = useQuery({
    queryKey: ["crew", crew.id, "home-zone"],
    queryFn: () => api<HomeZone>(`/v1/admin/crew/${crew.id}/home-zone`),
  });
  if (q.isError) return <ErrorState message="The home zones could not be loaded." onRetry={() => void q.refetch()} />;
  if (!q.data) return <Skeleton className="h-16 w-full" />;
  return <ZoneForm key={JSON.stringify(q.data)} crewId={crew.id} data={q.data} />;
}

export const section: CrewRulesSection = {
  id: "home-zone", title: "Home zones", order: 20, component: HomeZoneSection,
};
