import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { ConfirmProvider } from "../blocks/confirm";
import { TasksProvider } from "../blocks/tasks";
import { TooltipProvider } from "../ui/tooltip";

/**
 * Tests: the providers the Shell gives every page (confirmation dialog, long
 * tasks, tooltips). Render inside a router, as TasksProvider links to results.
 */
export function PortalProviders({ children }: { children: ReactNode }) {
  return (
    <TooltipProvider delayDuration={0}>
      <ConfirmProvider>
        <TasksProvider>{children}</TasksProvider>
      </ConfirmProvider>
    </TooltipProvider>
  );
}

/** Opens the dropdown labelled `label` and picks the choice named `choice`. */
export async function choose(label: string | RegExp, choice: string | RegExp) {
  await userEvent.click(screen.getByRole("combobox", { name: label }));
  await userEvent.click(await screen.findByRole("option", { name: choice }));
}

/** Presses the confirm button of the confirmation dialog. */
export async function confirmWith(name: string | RegExp) {
  const dialog = await screen.findByRole("alertdialog");
  await userEvent.click(within(dialog).getByRole("button", { name }));
}
