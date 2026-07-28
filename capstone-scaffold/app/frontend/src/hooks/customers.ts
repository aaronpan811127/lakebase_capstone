import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type {
  CustomerDetailOut,
  CustomerListOut,
  MetricsOut,
  NoteOut,
  SegmentOverrideOut,
} from "@/api/types";

export interface CustomerFilters {
  segment?: string;
  min_ltv?: number;
  max_churn?: number;
}

function listQuery(filters: CustomerFilters, page: number, pageSize: number): string {
  const p = new URLSearchParams();
  if (filters.segment) p.set("segment", filters.segment);
  if (filters.min_ltv != null) p.set("min_ltv", String(filters.min_ltv));
  if (filters.max_churn != null) p.set("max_churn", String(filters.max_churn));
  p.set("page", String(page));
  p.set("page_size", String(pageSize));
  return `/api/customers?${p.toString()}`;
}

export const useCustomers = (filters: CustomerFilters, page: number, pageSize = 25) =>
  useQuery({
    queryKey: ["customers", filters, page, pageSize],
    queryFn: () => apiGet<CustomerListOut>(listQuery(filters, page, pageSize)),
    staleTime: 10_000,
    placeholderData: (prev) => prev,
  });

export const useCustomer = (id: string) =>
  useQuery({
    queryKey: ["customer", id],
    queryFn: () => apiGet<CustomerDetailOut>(`/api/customers/${id}`),
    staleTime: 30_000,
  });

export const useMetrics = (id: string) =>
  useQuery({
    queryKey: ["metrics", id],
    queryFn: () => apiGet<MetricsOut>(`/api/customers/${id}/metrics`),
    staleTime: 60_000,
  });

export const useNotes = (id: string) =>
  useQuery({
    queryKey: ["notes", id],
    queryFn: () => apiGet<NoteOut[]>(`/api/customers/${id}/notes`),
    staleTime: 10_000,
  });

export const useSegmentOverride = (id: string) =>
  useQuery({
    queryKey: ["segment", id],
    queryFn: () => apiGet<SegmentOverrideOut | null>(`/api/customers/${id}/segment`),
    staleTime: 30_000,
  });

export function useAddNote(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (note_text: string) =>
      apiPost<NoteOut>(`/api/customers/${id}/notes`, { note_text }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notes", id] }),
  });
}

export function useOverrideSegment(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { override_segment: string; reason?: string }) =>
      apiPost<SegmentOverrideOut>(`/api/customers/${id}/segment`, v),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["segment", id] });
      qc.invalidateQueries({ queryKey: ["customer", id] });
    },
  });
}
