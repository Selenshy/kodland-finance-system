"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, ApiError } from "@/lib/api";
import { Role, User } from "@/lib/types";
import { useEntities } from "@/lib/entity-context";

const ROLES: Role[] = ["admin", "accountant", "viewer"];

export default function UsersAdminPage() {
  const queryClient = useQueryClient();
  const { entities } = useEntities();
  const { data: users = [], isLoading } = useQuery({ queryKey: ["users"], queryFn: () => apiRequest<User[]>("/api/users") });

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [entityIds, setEntityIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/users", {
        method: "POST",
        body: { email, password, full_name: fullName, global_role: role, entity_role_ids: entityIds },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setEmail(""); setPassword(""); setFullName(""); setEntityIds([]);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Failed to create user"),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) => apiRequest(`/api/users/${id}`, { method: "PATCH", body: { is_active } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Users</h1>

      <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-xs uppercase text-slate-500">
                <th className="pb-2">Email</th>
                <th className="pb-2">Name</th>
                <th className="pb-2">Role</th>
                <th className="pb-2">Entities</th>
                <th className="pb-2">Active</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-slate-100">
                  <td className="py-1.5">{u.email}</td>
                  <td className="py-1.5">{u.full_name}</td>
                  <td className="py-1.5 capitalize">{u.global_role}</td>
                  <td className="py-1.5">{u.entity_ids === null ? "All" : u.entity_ids.length}</td>
                  <td className="py-1.5">
                    <button onClick={() => toggleActiveMutation.mutate({ id: u.id, is_active: !u.is_active })} className={u.is_active ? "text-green-700" : "text-slate-400"}>
                      {u.is_active ? "Active" : "Disabled"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold">New User</h2>
        <form onSubmit={(e) => { e.preventDefault(); setError(null); createMutation.mutate(); }} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <input required type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
          <input required type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
          <input placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
          <select value={role} onChange={(e) => setRole(e.target.value as Role)} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
            {ROLES.map((r) => (<option key={r} value={r}>{r}</option>))}
          </select>

          <div className="col-span-2 sm:col-span-4">
            <label className="mb-1 block text-xs font-medium text-slate-500">Restrict to legal entities (leave empty for all)</label>
            <div className="flex flex-wrap gap-3">
              {entities.map((e) => (
                <label key={e.id} className="flex items-center gap-1 text-xs">
                  <input
                    type="checkbox"
                    checked={entityIds.includes(e.id)}
                    onChange={(ev) => setEntityIds(ev.target.checked ? [...entityIds, e.id] : entityIds.filter((id) => id !== e.id))}
                  />
                  {e.name}
                </label>
              ))}
            </div>
          </div>

          <button type="submit" disabled={createMutation.isPending} className="col-span-2 rounded bg-slate-900 px-4 py-2 text-sm text-white sm:col-span-1">
            Create User
          </button>
        </form>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
    </div>
  );
}
