import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "./api";
import { ChartOfAccount, Currency, Dimension } from "./types";

export function useAccounts(entityId: number | null) {
  return useQuery({
    queryKey: ["accounts", entityId],
    queryFn: () => apiRequest<ChartOfAccount[]>(`/api/legal-entities/${entityId}/accounts`),
    enabled: !!entityId,
  });
}

export function useCostCenters(entityId: number | null) {
  return useQuery({
    queryKey: ["cost-centers", entityId],
    queryFn: () => apiRequest<Dimension[]>(`/api/legal-entities/${entityId}/cost-centers`),
    enabled: !!entityId,
  });
}

export function useCounterparties(entityId: number | null) {
  return useQuery({
    queryKey: ["counterparties", entityId],
    queryFn: () => apiRequest<Dimension[]>(`/api/legal-entities/${entityId}/counterparties`),
    enabled: !!entityId,
  });
}

export function useProjects(entityId: number | null) {
  return useQuery({
    queryKey: ["projects", entityId],
    queryFn: () => apiRequest<Dimension[]>(`/api/legal-entities/${entityId}/projects`),
    enabled: !!entityId,
  });
}

export function useCurrencies() {
  return useQuery({
    queryKey: ["currencies"],
    queryFn: () => apiRequest<Currency[]>("/api/currencies"),
  });
}
