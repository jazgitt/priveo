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
 * What the toast says once a drop is saved: where the dragged card landed, so the admin can see it
 * (there is no Undo), then the other cards it moved, then any crew or service-hours warning.
 */
export function movedMessage(r: BatchMoveResult, moves: BatchMove[]): string {
  const dragged = moves[0] ? r.jobs.find((j) => j.id === moves[0].job_id) : undefined;
  let text = "Moved.";
  if (dragged && dragged.crew_id === null) text = `${dragged.registration} taken off its crew member.`;
  else if (dragged) text = `${dragged.registration} moved to ${dragged.crew_name} at ${dragged.start_time}.`;
  const others = moves.length - 1;
  if (others > 0) text += ` ${others} other ${others === 1 ? "job" : "jobs"} moved by hand.`;
  const warnings = r.warnings.map((w) => w.message).join(" ");
  return warnings ? `${text} ${warnings}` : text;
}

/**
 * Saves a batch of moves for the board under `boardKey`. The change is shown
 * at once; a refusal (overlap, or any other error) puts the board back and
 * shows the message in one toast. `onResult` gets the warnings of a saved batch.
 * `onSettled` gets the error of a refused batch, or null when it was saved, so the
 * page can offer the next step (the unfreeze code for a frozen day).
 */
export function useBatchMove(boardKey: QueryKey, onResult?: (result: BatchMoveResult) => void,
                             onSettled?: (error: unknown) => void) {
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
    success: (r, v) => movedMessage(r, v.moves),
    onSuccess: (r) => {
      onResult?.(r);
      onSettled?.(null);
      announceBoardChange();
    },
    onError: (e) => onSettled?.(e),
    invalidate: [boardKey],
  });
}
