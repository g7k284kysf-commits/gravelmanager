import { render, screen } from "@testing-library/react";
import { MetricCard } from "@/components/metric-card";

describe("MetricCard", () => {
  it("renders the metric and unit", () => {
    render(<MetricCard label="FTP" value={285} unit="W" />);
    expect(screen.getByText("FTP")).toBeInTheDocument();
    expect(screen.getByText("285")).toBeInTheDocument();
    expect(screen.getByText("W")).toBeInTheDocument();
  });
});

