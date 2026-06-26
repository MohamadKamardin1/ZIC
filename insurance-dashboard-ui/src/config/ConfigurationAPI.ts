import { apiFetchAuth } from "../lib/api";
import type { ChoicesResponse, WorkflowConfig } from "./ConfigurationTypes";

const CONFIG_BASE = "/api/v1/system-parameters/configuration";

async function extractData<T>(res: Response): Promise<T> {
  const json = await res.json();
  return json.data as T;
}

export async function fetchAllChoices(): Promise<ChoicesResponse> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/choices/`);
  if (!res.ok) throw new Error("Failed to load choices");
  return extractData<ChoicesResponse>(res);
}

export async function fetchChoiceList(code: string): Promise<{ value: string; label: string }[]> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/choices/${code}/`);
  if (!res.ok) return [];
  return extractData<{ value: string; label: string }[]>(res);
}

export async function fetchWorkflowConfig(): Promise<WorkflowConfig> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/workflows/`);
  if (!res.ok) throw new Error("Failed to load workflow config");
  return extractData<WorkflowConfig>(res);
}

export async function validateTransition(
  currentStatus: string,
  targetStatus: string,
): Promise<{ allowed: boolean; allowedTransitions: string[] }> {
  const res = await apiFetchAuth(`${CONFIG_BASE}/workflows/validate-transition/`, {
    method: "POST",
    body: JSON.stringify({ current_status: currentStatus, target_status: targetStatus }),
  });
  if (!res.ok) throw new Error("Failed to validate transition");
  return extractData<{ allowed: boolean; allowedTransitions: string[] }>(res);
}

export async function invalidateConfigCache(pattern?: string): Promise<void> {
  await apiFetchAuth(`${CONFIG_BASE}/cache/invalidate/`, {
    method: "POST",
    body: JSON.stringify({ pattern }),
  });
}
