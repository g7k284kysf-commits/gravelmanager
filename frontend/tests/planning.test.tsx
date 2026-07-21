import { render, screen } from "@testing-library/react";
import { PlanningOverview } from "@/components/planning/planning-overview";
import { PriorityBadge } from "@/components/planning/priority-badge";
import { getCompetitions, getGoals } from "@/lib/api";

vi.mock("@/lib/api", () => ({ getGoals: vi.fn(), getCompetitions: vi.fn() }));

it.each(["A", "B", "C"] as const)("renders the %s race priority badge", (priority) => {
  render(<PriorityBadge priority={priority} />);
  expect(screen.getByLabelText(`Race priority ${priority}`)).toHaveTextContent(priority);
});

it("renders goal hierarchy and competition priorities", async () => {
  vi.mocked(getGoals).mockResolvedValue([
    { id: 1, parent_goal_id: null, title: "Season peak", goal_type: "season", priority: "critical", target_date: "2027-06-01", status: "active" },
    { id: 2, parent_goal_id: 1, title: "Heat adaptation", goal_type: "heat_adaptation", priority: "high", target_date: null, status: "active" },
  ]);
  vi.mocked(getCompetitions).mockResolvedValue([
    { id: 1, name: "Unbound", start_date: "2027-06-01", end_date: "2027-06-01", race_priority: "A", status: "active", discipline: "Gravel" },
  ]);
  render(<PlanningOverview />);
  expect(await screen.findByText("Season peak")).toBeInTheDocument();
  expect(screen.getByText("Heat adaptation")).toBeInTheDocument();
  expect(screen.getByText("Unbound")).toBeInTheDocument();
  expect(screen.getByLabelText("Race priority A")).toBeInTheDocument();
});

it("renders empty planning states", async () => {
  vi.mocked(getGoals).mockResolvedValue([]);
  vi.mocked(getCompetitions).mockResolvedValue([]);
  render(<PlanningOverview />);
  expect(await screen.findByText(/No goals yet/)).toBeInTheDocument();
  expect(screen.getByText(/No competitions planned/)).toBeInTheDocument();
});
