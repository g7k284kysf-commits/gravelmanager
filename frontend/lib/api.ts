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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window === "undefined" ? null : localStorage.getItem("access_token");
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
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
