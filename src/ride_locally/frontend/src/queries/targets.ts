import { apiFetch } from "../api/client"
import type { Target } from "../pages/add-target/page";

export type GetTargetsQuery = {
  offset: number;
  limit: number;
  search?: string;
  is_active?: boolean;
}

function toStringRecord<T extends Record<string, unknown>>(o: T): Record<string, string> {
  return Object.fromEntries(
    Object.entries(o)
      .filter(([, v]) => v !== undefined && v !== null)
      .map(([k, v]) => [k, String(v)])
  );
}

export async function get_targets(query: GetTargetsQuery) {
  const qs = new URLSearchParams(toStringRecord(query))

  const res = await apiFetch(`/targets/get?${qs.toString()}`, { method: "GET" });

  const targets: Target[] = await res.json()

  return targets;
}

