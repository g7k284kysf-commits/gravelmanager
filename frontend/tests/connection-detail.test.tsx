import { render, screen } from "@testing-library/react";
import { ConnectionDetail } from "@/components/integrations/connection-detail";
import {
  getConnection,
  getIntegrationEvents,
  getProviders,
  getSyncs,
  type IntegrationConnection,
  type Provider,
} from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getConnection: vi.fn(),
  getIntegrationEvents: vi.fn(),
  getProviders: vi.fn(),
  getSyncs: vi.fn(),
  revokeConnection: vi.fn(),
  startConnectionSync: vi.fn(),
  testConnection: vi.fn(),
}));

const baseConnection: IntegrationConnection = {
  id: 4,
  provider_key: "manual_upload",
  display_name: "Manual upload",
  status: "connected",
  scopes: [],
  configuration: {},
  last_successful_sync_at: null,
  last_sync_attempt_at: null,
  last_error_code: null,
  last_error_message: null,
  created_at: "2026-07-21T00:00:00Z",
  updated_at: "2026-07-21T00:00:00Z",
  revoked_at: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getConnection).mockResolvedValue(baseConnection);
  vi.mocked(getSyncs).mockResolvedValue([]);
  vi.mocked(getIntegrationEvents).mockResolvedValue([]);
});

it("enables only operations supported by manual upload", async () => {
  const provider: Provider = {
    provider_key: "manual_upload",
    display_name: "Manual upload",
    capabilities: ["file_import"],
    availability: "manual_import_only",
    description: "Upload files.",
    operational: true,
  };
  vi.mocked(getProviders).mockResolvedValue([provider]);

  render(<ConnectionDetail connectionId={4} />);

  expect(await screen.findByRole("button", { name: "Test connection" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Start sync" })).toBeDisabled();
  expect(getSyncs).toHaveBeenCalledWith(4);
  expect(getIntegrationEvents).toHaveBeenCalledWith(4);
});

it("disables live actions for coming-soon providers", async () => {
  vi.mocked(getConnection).mockResolvedValue({
    ...baseConnection,
    provider_key: "garmin",
    display_name: "Garmin Connect",
    status: "pending",
  });
  vi.mocked(getProviders).mockResolvedValue([
    {
      provider_key: "garmin",
      display_name: "Garmin Connect",
      capabilities: ["oauth", "polling"],
      availability: "coming_soon",
      description: "Provider foundation.",
      operational: false,
    },
  ]);

  render(<ConnectionDetail connectionId={4} />);

  expect(await screen.findByText(/provider is coming soon/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Test connection" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Start sync" })).toBeDisabled();
});
