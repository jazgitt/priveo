import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AlertEmailSettings } from "./AlertEmailSettings";
import { sharedReadOptions } from "../../api/queryDefaults";

afterEach(() => vi.unstubAllGlobals());

it("saves email opt-out and retains unsaved edits during external refresh", async () => {
  let saved: unknown;
  vi.stubGlobal("fetch", vi.fn(async (_path: string, options?: RequestInit) => {
    if (options?.method === "PUT") saved = JSON.parse(options.body as string);
    return new Response(JSON.stringify(saved ?? { email: "old@example.com", enabled: true }), { status: 200 });
  }));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={qc}><AlertEmailSettings /></QueryClientProvider>);
  const input = await screen.findByLabelText("Alert email address");
  fireEvent.change(input, { target: { value: "edited@example.com" } });
  qc.setQueryData(["alert-email-preferences"], { email: "external@example.com", enabled: true });
  expect(input).toHaveValue("edited@example.com");
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByText("Save alert email preferences"));
  await screen.findByText("Alert email preferences saved.");
  expect(saved).toEqual({ email: "edited@example.com", enabled: false });
  qc.clear();
});

it("open queries refetch external writes on the shared cadence", async () => {
  const qc = new QueryClient({ defaultOptions: { queries: { ...sharedReadOptions, retry: false, refetchInterval: 20 } } });
  let value = "before";
  const { useQuery } = await import("@tanstack/react-query");
  function Read() {
    const query = useQuery({ queryKey: ["two-client"], queryFn: async () => value });
    return <p>{query.data}</p>;
  }
  render(<QueryClientProvider client={qc}><Read /></QueryClientProvider>);
  await screen.findByText("before");
  value = "after";
  await waitFor(() => expect(screen.getByText("after")).toBeInTheDocument());
  qc.clear();
});
