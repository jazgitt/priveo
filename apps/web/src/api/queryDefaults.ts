// Open screens observe writes made on another device within 30 seconds.
// Background polling is paused; focus/reconnection refresh immediately.
export const sharedReadOptions = {
  refetchInterval: 30_000,
  refetchIntervalInBackground: false,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
} as const;
