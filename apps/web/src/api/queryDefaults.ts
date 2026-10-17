// Open screens observe writes made on another device within 30 seconds.
// Background polling is paused; focus/reconnection refresh immediately.
// Data younger than 10 seconds is shown without asking the API again, so
// moving between pages does not refetch everything.
export const sharedReadOptions = {
  staleTime: 10_000,
  refetchInterval: 30_000,
  refetchIntervalInBackground: false,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
} as const;
