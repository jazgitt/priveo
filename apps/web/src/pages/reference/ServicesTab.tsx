import { useState } from "react";

import { Button, Card, TextField, useToast } from "../../components";
import { fieldError, useDirectory, useDirMutation } from "./api";
import { QueryState } from "./common";
import type { ServiceRow } from "./types";

function ServiceEditor({ row }: { row: ServiceRow }) {
  const toast = useToast();
  const save = useDirMutation();
  const [duration, setDuration] = useState(String(row.duration_minutes));
  const [photos, setPhotos] = useState(String(row.min_photos));
  const [videos, setVideos] = useState(String(row.min_videos));

  return (
    <Card title={row.name}>
      <div className="ref-toolbar">
        <TextField label={`Duration in minutes, ${row.name}`} type="number" value={duration}
                   error={fieldError(save.error, "duration_minutes")}
                   onChange={(e) => setDuration(e.target.value)} />
        <TextField label={`Minimum photos, ${row.name}`} type="number" value={photos}
                   error={fieldError(save.error, "min_photos")}
                   onChange={(e) => setPhotos(e.target.value)} />
        <TextField label={`Minimum videos, ${row.name}`} type="number" value={videos}
                   error={fieldError(save.error, "min_videos")}
                   onChange={(e) => setVideos(e.target.value)} />
        <Button busy={save.isPending} aria-label={`Save ${row.name}`}
                onClick={() => save.mutate({
                  path: `/services/${encodeURIComponent(row.name)}`, method: "PATCH",
                  body: { duration_minutes: Number(duration), min_photos: Number(photos),
                          min_videos: Number(videos) },
                }, { onSuccess: () => toast.show("Service saved.", "ok") })}>Save</Button>
      </div>
    </Card>
  );
}

/** Service durations and the proof the crew must upload (ADM-SVS-09, ADM-CHK-06). */
export function ServicesTab() {
  const list = useDirectory<ServiceRow[]>("/services");
  return (
    <QueryState query={list}>
      {(rows) => (
        <div className="ref-stack">
          {rows.map((r) => (
            <ServiceEditor key={`${r.name}-${r.duration_minutes}-${r.min_photos}-${r.min_videos}`}
                           row={r} />
          ))}
        </div>
      )}
    </QueryState>
  );
}
