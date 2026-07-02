import { apiFetch } from "../api/client"
import type { Target } from "../pages/add-target/page";

export type TargetActiveState = "true" | "false" | "both";

export type GetTargetsQuery = {
  page: number;
  per_page: number;
  search?: string;
  active?: TargetActiveState;
}

export type GetTargetsResponse = {
  items: Target[];
  total: number;
  page: number;
  per_page: number;
}

function toStringRecord<T extends Record<string, unknown>>(o: T): Record<string, string> {
  return Object.fromEntries(
    Object.entries(o)
      .filter(([, v]) => v !== undefined && v !== null)
      .map(([k, v]) => [k, String(v)])
  );
}

export async function get_targets(query: GetTargetsQuery): Promise<GetTargetsResponse> {
  const qs = new URLSearchParams(toStringRecord(query))

  const res = await apiFetch(`/targets?${qs.toString()}`, { method: "GET" });

  const payload: GetTargetsResponse = await res.json()

  return payload;
}

