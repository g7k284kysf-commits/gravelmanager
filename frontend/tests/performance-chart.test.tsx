import { render, screen } from "@testing-library/react";
import { PerformanceChart } from "@/components/performance/performance-chart";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ComposedChart: ({ children }: { children: React.ReactNode }) => <svg>{children}</svg>,
  Area: () => null,
  Bar: () => null,
  CartesianGrid: () => null,
  Legend: () => null,
  Line: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

it("maps every daily value into an accessible data table", () => {
  render(
    <PerformanceChart
      points={[
        { date: "2026-03-31", daily_tss: 90, ctl: 40.2, atl: 45.8, tsb: -5.6, ramp_rate: 3.1 },
      ]}
    />,
  );
  expect(screen.getByTestId("performance-chart")).toHaveClass("w-full");
  expect(screen.getByRole("table", { name: "Daily performance chart values" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "90" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "40.2" })).toBeInTheDocument();
});
