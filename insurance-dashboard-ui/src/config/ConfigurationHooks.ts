import { useState, useEffect, useCallback } from "react";
import { configCache } from "./ConfigurationCache";
import { fetchAllChoices, fetchWorkflowConfig } from "./ConfigurationAPI";
import type { ChoicesResponse, WorkflowConfig } from "./ConfigurationTypes";

export function useChoices(): ChoicesResponse | null {
  const [choices, setChoices] = useState<ChoicesResponse | null>(() =>
    configCache.get<ChoicesResponse>("choices"),
  );

  useEffect(() => {
    if (choices) return;
    let active = true;
    fetchAllChoices()
      .then((data) => {
        if (!active) return;
        configCache.set("choices", data);
        setChoices(data);
      })
      .catch(() => {});
    return () => { active = false };
  }, [choices]);

  return choices;
}

export function useWorkflowConfig(): WorkflowConfig | null {
  const [config, setConfig] = useState<WorkflowConfig | null>(() =>
    configCache.get<WorkflowConfig>("workflow"),
  );

  useEffect(() => {
    if (config) return;
    let active = true;
    fetchWorkflowConfig()
      .then((data) => {
        if (!active) return;
        configCache.set("workflow", data);
        setConfig(data);
      })
      .catch(() => {});
    return () => { active = false };
  }, [config]);

  return config;
}

export function useStatusLabel(status: string): string {
  const config = useWorkflowConfig();
  if (!config?.status_labels) return status;
  return config.status_labels[status] ?? status;
}

const STATUS_BG: Record<string, string> = {
  ACTIVE: "var(--color-bg-success-soft)",
  DRAFT: "var(--color-bg-muted)",
  SUBMITTED: "var(--color-bg-info-soft)",
  UNDER_REVIEW: "var(--color-bg-info-soft)",
  PENDING_DOCUMENTS: "var(--color-bg-warning-soft)",
  COMPLIANCE_CHECK: "var(--color-bg-warning-soft)",
  APPROVED: "var(--color-bg-success-soft)",
  CONVERTED: "var(--color-bg-success-soft)",
  REJECTED: "var(--color-bg-destructive-soft)",
  SUSPENDED: "var(--color-bg-warning-soft)",
};

const STATUS_TEXT: Record<string, string> = {
  ACTIVE: "var(--color-text-success-soft)",
  DRAFT: "var(--color-text-muted)",
  SUBMITTED: "var(--color-text-info-soft)",
  UNDER_REVIEW: "var(--color-text-info-soft)",
  PENDING_DOCUMENTS: "var(--color-text-warning-soft)",
  COMPLIANCE_CHECK: "var(--color-text-warning-soft)",
  APPROVED: "var(--color-text-success-soft)",
  CONVERTED: "var(--color-text-success-soft)",
  REJECTED: "var(--color-text-destructive-soft)",
  SUSPENDED: "var(--color-text-warning-soft)",
};

export function useStatusColor(status: string): string {
  return STATUS_BG[status] ?? "var(--color-bg-muted)";
}

export function useStatusTextColor(status: string): string {
  return STATUS_TEXT[status] ?? "var(--color-text-muted)";
}
