// Saving a drop: the board shows the move at once, puts it back if the server
// refuses, and tells the other tabs of this browser when it is saved.
import { useQueryClient, type QueryKey } from "@tanstack/react-query";

import { useAppMutation } from "@/blocks/mutation";

import { batchMoveJobs, hhmm, type AdminJob, type Board, type BatchMove, type BatchMoveResult } from "../api";
import type { DropPlan } from "./geometry";
import { announceBoardChange } from "./sync";

/** The moves for a drop into one lane: the dragged card, then every card the drop shifts (all marked By hand). */
export function movesFor(crewId: string | null, draggedId: string, plan: DropPlan): BatchMove[] {
  const placed = crewId !== null;
  return [
    { job_id: draggedId, crew_id: crewId, start_minute: placed ? plan.start : null },
    ...plan.shifts.map((s) => ({ job_id: s.id, crew_id: crewId, start_minute: s.start })),
  ];
}

/**
 * The board as it looks once `moves` are saved, for the optimistic update.
 * Same rules as the server: a moved job is By hand, and a job with no crew or
 * no start time is Unscheduled.
 */
export function applyMovesToBoard(board: Board, moves: BatchMove[]): Board {
  const byJob = new Map(moves.map((m) => [m.job_id, m]));
  const jobs = board.jobs.map((j): AdminJob => {
    const m = byJob.get(j.id);
    if (!m) return j;
    const crewName = m.crew_id === null ? null : board.crew.find((c) => c.id === m.crew_id)?.name ?? null;
    const placed = m.crew_id !== null && m.start_minute !== null;
    return {
      ...j,
      crew_id: m.crew_id,
      crew_name: crewName,
      manual: true,
      start_minute: placed ? m.start_minute : null,
      start_time: placed ? hhmm(m.start_minute!) : null,
      end_time: placed ? hhmm(m.start_minute! + j.duration_minutes) : null,
    };
  });
  return { ...board, jobs };
}

export interface BatchMoveVars {
  moves: BatchMove[];
  override?: boolean;
}

/**
 * Saves a batch of moves for the board under `boardKey`. The change is shown
 * at once; a refusal (overlap, or any other error) puts the board back and
 * shows the message in one toast. `onResult` gets the warnings of a saved batch.
 */
export function useBatchMove(boardKey: QueryKey, onResult?: (result: BatchMoveResult) => void) {
  const qc = useQueryClient();
  return useAppMutation<BatchMoveVars, BatchMoveResult>({
    mutationFn: (v) => batchMoveJobs(v.moves, Boolean(v.override)),
    pending: false,
    optimistic: async (v) => {
      await qc.cancelQueries({ queryKey: boardKey });
      const before = qc.getQueryData<Board>(boardKey);
      if (before) qc.setQueryData<Board>(boardKey, applyMovesToBoard(before, v.moves));
      return () => {
        if (before) qc.setQueryData<Board>(boardKey, before);
      };
    },
    success: (r) => (r.warnings.length ? r.warnings.map((w) => w.message).join(" ") : "Moved."),
    onSuccess: (r) => {
      onResult?.(r);
      announceBoardChange();
    },
    invalidate: [boardKey],
  });
}
