import { useState } from "react";

import { Field } from "@/blocks/fields";
import { BusyButton } from "@/blocks/FormDialog";
import { Panel } from "@/blocks/layout";
import { Input } from "@/ui/input";

import { fieldError, useDirectory, useDirSave } from "./api";
import { QueryState } from "./common";
import type { ServiceRow } from "./types";

function ServiceEditor({ row }: { row: ServiceRow }) {
  const save = useDirSave();
  const [duration, setDuration] = useState(String(row.duration_minutes));
  const [photos, setPhotos] = useState(String(row.min_photos));
  const [videos, setVideos] = useState(String(row.min_videos));
  const changed = duration !== String(row.duration_minutes) || photos !== String(row.min_photos) || videos !== String(row.min_videos);

  return (
    <Panel title={row.name}>
      <form className="grid grid-cols-1 items-end gap-4 sm:grid-cols-[repeat(3,minmax(0,11rem))_auto]"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate({
                path: `/services/${encodeURIComponent(row.name)}`, method: "PATCH", done: `${row.name} saved.`,
                body: { duration_minutes: Number(duration), min_photos: Number(photos), min_videos: Number(videos) },
              });
            }}>
        <Field label="Duration in minutes" error={fieldError(save.error, "duration_minutes")}>
          {(p) => <Input {...p} aria-label={`Duration in minutes, ${row.name}`} type="number" value={duration} onChange={(e) => setDuration(e.target.value)} />}
        </Field>
        <Field label="Minimum photos" error={fieldError(save.error, "min_photos")}>
          {(p) => <Input {...p} aria-label={`Minimum photos, ${row.name}`} type="number" value={photos} onChange={(e) => setPhotos(e.target.value)} />}
        </Field>
        <Field label="Minimum videos" error={fieldError(save.error, "min_videos")}>
          {(p) => <Input {...p} aria-label={`Minimum videos, ${row.name}`} type="number" value={videos} onChange={(e) => setVideos(e.target.value)} />}
        </Field>
        <BusyButton type="submit" busy={save.isPending} disabled={!changed} aria-label={`Save ${row.name}`}>Save</BusyButton>
      </form>
    </Panel>
  );
}

/** Service durations and the proof the crew must upload (ADM-SVS-09, ADM-CHK-06). */
export function ServicesTab() {
  const list = useDirectory<ServiceRow[]>("/services");
  return (
    <QueryState query={list}>
      {(rows) => (
        <div className="flex flex-col gap-6">
          {rows.map((r) => <ServiceEditor key={`${r.name}-${r.duration_minutes}-${r.min_photos}-${r.min_videos}`} row={r} />)}
        </div>
      )}
    </QueryState>
  );
}
