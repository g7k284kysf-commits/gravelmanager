import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PerformanceManager } from "@/components/performance/performance-manager";
import { getPerformanceChart, getPerformanceSummary } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getPerformanceSummary: vi.fn(),
  getPerformanceChart: vi.fn(),
}));

vi.mock("@/components/performance/performance-chart", () => ({
  PerformanceChart: ({ points }: { points: Array<{ date: string }> }) => (
    <div data-testid="performance-chart">{points.map((point) => point.date).join(",")}</div>
  ),
}));

const summary = {
  ctl: 42.25,
  atl: 51.5,
  tsb: -9.25,
  seven_day_tss: 420,
  twenty_eight_day_tss: 1480,
  seven_day_training_hours: 8.5,
  twenty_eight_day_training_hours: 31,
  ramp_rate: 4.75,
  twenty_eight_day_ctl_change: 9.2,
};

const chart = {
  range: "90d" as const,
  start_date: "2026-01-01",
  end_date: "2026-03-31",
  points: [{ date: "2026-03-31", daily_tss: 80, ctl: 42.25, atl: 51.5, tsb: -9.25, ramp_rate: 4.75 }],
};

const summaryMock = vi.mocked(getPerformanceSummary);
const chartMock = vi.mocked(getPerformanceChart);

beforeEach(() => {
  vi.clearAllMocks();
  summaryMock.mockResolvedValue(summary);
  chartMock.mockResolvedValue(chart);
});

it("shows a stable loading state while requests are pending", () => {
  summaryMock.mockReturnValue(new Promise(() => undefined));
  chartMock.mockReturnValue(new Promise(() => undefined));
  render(<PerformanceManager />);
  expect(screen.getByRole("status", { name: "Loading performance data" })).toBeInTheDocument();
});

it("renders calculated cards and chart data", async () => {
  render(<PerformanceManager />);
  expect(await screen.findByText("Performance Manager")).toBeInTheDocument();
  expect(screen.getByText("42.3")).toBeInTheDocument();
  expect(screen.getByText("-9.3")).toBeInTheDocument();
  expect(screen.getByText("1480.0")).toBeInTheDocument();
  expect(screen.getByTestId("performance-chart")).toHaveTextContent("2026-03-31");
});

it("requests a new series when the athlete changes range", async () => {
  render(<PerformanceManager />);
  await screen.findByText("Performance Manager");
  fireEvent.click(screen.getByRole("button", { name: "28d" }));
  await waitFor(() => expect(chartMock).toHaveBeenLastCalledWith("28d"));
  expect(screen.getByRole("button", { name: "28d" })).toHaveAttribute("aria-pressed", "true");
});

it("renders the empty-history guidance instead of a fake chart", async () => {
  chartMock.mockResolvedValue({ ...chart, points: [] });
  render(<PerformanceManager />);
  expect(await screen.findByText("Build your performance curve")).toBeInTheDocument();
  expect(screen.queryByTestId("performance-chart")).not.toBeInTheDocument();
});

it("shows an error and retries both requests", async () => {
  summaryMock.mockRejectedValueOnce(new Error("Network unavailable"));
  render(<PerformanceManager />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Network unavailable");
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("42.3")).toBeInTheDocument();
  expect(summaryMock).toHaveBeenCalledTimes(2);
});

it("keeps range controls usable on narrow screens", async () => {
  render(<PerformanceManager />);
  await screen.findByText("Performance Manager");
  expect(screen.getByLabelText("Chart range")).toHaveClass("overflow-x-auto");
});
