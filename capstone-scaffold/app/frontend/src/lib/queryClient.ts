import { QueryClient } from "@tanstack/react-query";

// Per-key staleTimes are set on individual queries; these are sane defaults.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
