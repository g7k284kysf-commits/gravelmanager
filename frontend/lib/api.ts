const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type DashboardMetrics = {
  ftp: number | null;
  ctl: number;
  atl: number;
  tsb: number;
  weekly_hours: number;
  weekly_tss: number;
};

export type Training = {
  id: number;
  date: string;
  sport: string;
  duration_minutes: number;
  distance_km: number | null;
  elevation_m: number | null;
  tss: number | null;
};

export type PerformanceRange = "28d" | "90d" | "180d" | "365d";

export type PerformanceSummary = {
  ctl: number;
  atl: number;
  tsb: number;
  seven_day_tss: number;
  twenty_eight_day_tss: number;
  seven_day_training_hours: number;
  twenty_eight_day_training_hours: number;
  ramp_rate: number;
  twenty_eight_day_ctl_change: number;
};

export type PerformancePoint = {
  date: string;
  daily_tss: number;
  ctl: number;
  atl: number;
  tsb: number;
  ramp_rate: number;
};

export type PerformanceChartResponse = {
  range: PerformanceRange;
  start_date: string;
  end_date: string;
  points: PerformancePoint[];
};

export type IntegrationCapability =
  | "oauth"
  | "file_import"
  | "activity_import"
  | "planned_workout_import"
  | "planned_workout_export"
  | "wellness_import"
  | "health_metrics_import"
  | "route_import"
  | "webhook"
  | "polling";

export type Provider = {
  provider_key: string;
  display_name: string;
  capabilities: IntegrationCapability[];
  availability: "coming_soon" | "manual_import_only";
  description: string;
};

export type IntegrationConnection = {
  id: number;
  provider_key: string;
  display_name: string;
  status: "disconnected" | "pending" | "connected" | "degraded" | "error" | "revoked";
  scopes: string[];
  configuration: Record<string, unknown>;
  last_successful_sync_at: string | null;
  last_sync_attempt_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  created_at: string;
  updated_at: string;
  revoked_at: string | null;
};

export type IntegrationSync = {
  id: number;
  connection_id: number;
  provider_key: string;
  sync_type: "full" | "incremental" | "manual" | "webhook" | "file_import";
  status: "queued" | "running" | "succeeded" | "partially_succeeded" | "failed" | "cancelled";
  correlation_id: string;
  requested_at: string;
  completed_at: string | null;
  records_created: number;
  records_updated: number;
  records_skipped: number;
  records_failed: number;
  error_message: string | null;
};

export type ImportFile = {
  id: number;
  original_filename: string;
  file_extension: string;
  file_size_bytes: number;
  status: "uploaded" | "validating" | "queued" | "processing" | "succeeded" | "partially_succeeded" | "failed" | "rejected";
  uploaded_at: string;
  error_message: string | null;
  metadata: Record<string, unknown> & {
    records_created?: number;
    records_updated?: number;
    records_skipped?: number;
    records_failed?: number;
  };
};

export type IntegrationEvent = {
  id: number;
  event_type: string;
  severity: "info" | "warning" | "error";
  provider_key: string;
  connection_id: number | null;
  message: string;
  created_at: string;
};

export type Goal = {
  id: number;
  parent_goal_id: number | null;
  title: string;
  goal_type: string;
  priority: string;
  target_date: string | null;
  status: string;
};

export type Competition = {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  race_priority: "A" | "B" | "C";
  status: string;
  discipline: string | null;
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window === "undefined" ? null : localStorage.getItem("access_token");
  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail ?? "The request could not be completed");
  }
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

export async function authenticate(mode: "login" | "register", email: string, password: string) {
  return request<{ access_token: string }>(`/auth/${mode}`, { method: "POST", body: JSON.stringify({ email, password }) });
}

export const getDashboard = () => request<DashboardMetrics>("/dashboard");
export const getTrainings = () => request<Training[]>("/trainings?limit=5");
export const getPerformanceSummary = () =>
  request<PerformanceSummary>("/performance/summary");
export const getPerformanceChart = (range: PerformanceRange) =>
  request<PerformanceChartResponse>(`/performance/chart?range=${range}`);

export const getProviders = () => request<Provider[]>("/integrations/providers");
export const getConnections = () =>
  request<IntegrationConnection[]>("/integrations/connections");
export const getConnection = (id: number) =>
  request<IntegrationConnection>(`/integrations/connections/${id}`);
export const createConnection = (providerKey: string) =>
  request<IntegrationConnection>("/integrations/connections", {
    method: "POST",
    body: JSON.stringify({ provider_key: providerKey }),
  });
export const testConnection = (id: number) =>
  request<{ supported: boolean; succeeded: boolean; message: string }>(
    `/integrations/connections/${id}/test`,
    { method: "POST" },
  );
export const revokeConnection = (id: number) =>
  request<IntegrationConnection>(`/integrations/connections/${id}/revoke`, {
    method: "POST",
  });
export const startConnectionSync = (id: number) =>
  request<IntegrationSync>(`/integrations/connections/${id}/sync`, {
    method: "POST",
    body: JSON.stringify({ sync_type: "manual" }),
  });
export const getSyncs = () => request<IntegrationSync[]>("/integrations/syncs");
export const getIntegrationEvents = () =>
  request<IntegrationEvent[]>("/integrations/events");
export const getImports = () => request<ImportFile[]>("/imports/files");
export const uploadImport = (file: File) => {
  const body = new FormData();
  body.append("file", file);
  return request<ImportFile>("/imports/files", { method: "POST", body });
};
export const processImport = (id: number) =>
  request<{ id: number; status: ImportFile["status"]; message: string }>(
    `/imports/files/${id}/process`,
    { method: "POST" },
  );
export const getGoals = () => request<Goal[]>("/planning/goals");
export const getCompetitions = () =>
  request<Competition[]>("/planning/competitions");
