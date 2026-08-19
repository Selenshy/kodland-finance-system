"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "./api";
import { LegalEntity } from "./types";
import { useAuth } from "./auth-context";

type EntityContextValue = {
  entities: LegalEntity[];
  isLoading: boolean;
  currentEntityId: number | null;
  currentEntity: LegalEntity | null;
  setCurrentEntityId: (id: number) => void;
  refetch: () => void;
};

const EntityContext = createContext<EntityContextValue | null>(null);

export function EntityProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [currentEntityId, setCurrentEntityIdState] = useState<number | null>(null);

  const { data: entities = [], isLoading, refetch } = useQuery({
    queryKey: ["legal-entities"],
    queryFn: () => apiRequest<LegalEntity[]>("/api/legal-entities"),
    enabled: !!user,
  });

  useEffect(() => {
    if (currentEntityId !== null) return;
    const stored = typeof window !== "undefined" ? window.localStorage.getItem("current_entity_id") : null;
    if (stored && entities.some((e) => e.id === Number(stored))) {
      setCurrentEntityIdState(Number(stored));
    } else if (entities.length > 0) {
      setCurrentEntityIdState(entities[0].id);
    }
  }, [entities, currentEntityId]);

  const setCurrentEntityId = (id: number) => {
    setCurrentEntityIdState(id);
    if (typeof window !== "undefined") window.localStorage.setItem("current_entity_id", String(id));
  };

  const currentEntity = entities.find((e) => e.id === currentEntityId) || null;

  return (
    <EntityContext.Provider value={{ entities, isLoading, currentEntityId, currentEntity, setCurrentEntityId, refetch }}>
      {children}
    </EntityContext.Provider>
  );
}

export function useEntities() {
  const ctx = useContext(EntityContext);
  if (!ctx) throw new Error("useEntities must be used within EntityProvider");
  return ctx;
}
