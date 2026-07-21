import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { IntegrationManager, validateUpload } from "@/components/integrations/integration-manager";
import {
  ApiError,
  getConnections,
  getImports,
  getProviders,
  getSyncs,
  processImport,
  uploadImport,
  type ImportFile,
  type IntegrationConnection,
  type IntegrationSync,
  type Provider,
} from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getProviders: vi.fn(),
  getConnections: vi.fn(),
  getImports: vi.fn(),
  getSyncs: vi.fn(),
  createConnection: vi.fn(),
  uploadImport: vi.fn(),
  processImport: vi.fn(),
}));

const providerData: Provider[] = [
  { provider_key: "manual_upload", display_name: "Manual upload", capabilities: ["file_import"], availability: "manual_import_only", description: "Upload files.", operational: true },
  { provider_key: "garmin", display_name: "Garmin Connect", capabilities: ["oauth", "polling"], availability: "coming_soon", description: "Provider foundation.", operational: false },
];
const connection: IntegrationConnection = { id: 4, provider_key: "manual_upload", display_name: "Manual upload", status: "connected", scopes: [], configuration: {}, last_successful_sync_at: null, last_sync_attempt_at: null, last_error_code: null, last_error_message: null, created_at: "2026-07-21T00:00:00Z", updated_at: "2026-07-21T00:00:00Z", revoked_at: null };
const imported: ImportFile = { id: 7, original_filename: "ride.csv", file_extension: "csv", file_size_bytes: 20, status: "succeeded", uploaded_at: "2026-07-21T00:00:00Z", error_message: null, metadata: { records_created: 1 } };
const sync: IntegrationSync = { id: 8, connection_id: 4, provider_key: "manual_upload", sync_type: "manual", status: "succeeded", correlation_id: "sync-1", requested_at: "2026-07-21T00:00:00Z", completed_at: "2026-07-21T00:01:00Z", records_created: 2, records_updated: 0, records_skipped: 1, records_failed: 0, error_message: null };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getProviders).mockResolvedValue([...providerData]);
  vi.mocked(getConnections).mockResolvedValue([connection]);
  vi.mocked(getImports).mockResolvedValue([imported]);
  vi.mocked(getSyncs).mockResolvedValue([sync]);
});

it("renders provider status, import history, and sync history", async () => {
  render(<IntegrationManager />);
  expect(await screen.findByText("Garmin Connect")).toBeInTheDocument();
  expect(screen.getByText("coming soon")).toBeInTheDocument();
  expect(screen.getByText("ride.csv")).toBeInTheDocument();
  expect(screen.getByText("2 created · 1 skipped · 0 failed")).toBeInTheDocument();
});

it("shows a loading state and empty histories", async () => {
  vi.mocked(getProviders).mockReturnValue(new Promise(() => undefined));
  render(<IntegrationManager />);
  expect(screen.getByRole("status", { name: "Loading integrations" })).toBeInTheDocument();

  vi.mocked(getProviders).mockResolvedValue([...providerData]);
  vi.mocked(getImports).mockResolvedValue([]);
  vi.mocked(getSyncs).mockResolvedValue([]);
  render(<IntegrationManager />);
  expect(await screen.findByText("No files imported yet.")).toBeInTheDocument();
  expect(screen.getByText("No synchronizations have run yet.")).toBeInTheDocument();
});

it("validates file extension, empty files, and maximum size", () => {
  expect(validateUpload(new File(["x"], "malware.exe"))).toMatch("FIT");
  expect(validateUpload(new File([], "empty.csv"))).toMatch("empty");
  const oversized = new File([new Uint8Array(25 * 1024 * 1024 + 1)], "huge.fit");
  expect(validateUpload(oversized)).toMatch("25 MB");
});

it("uploads, processes, and refreshes a valid file", async () => {
  vi.mocked(uploadImport).mockResolvedValue({ ...imported, status: "uploaded" });
  vi.mocked(processImport).mockResolvedValue({ id: 7, status: "succeeded", message: "done" });
  render(<IntegrationManager />);
  const input = await screen.findByLabelText("Upload training file");
  fireEvent.change(input, { target: { files: [new File(["a,b\n1,2"], "ride.csv", { type: "text/csv" })] } });
  await waitFor(() => expect(uploadImport).toHaveBeenCalled());
  await waitFor(() => expect(processImport).toHaveBeenCalledWith(7));
  expect(await screen.findByText("Import finished. Review the result below.")).toBeInTheDocument();
});

it("shows safe upload errors without exposing backend details", async () => {
  vi.mocked(uploadImport).mockRejectedValue(new Error("raw database failure"));
  render(<IntegrationManager />);
  const input = await screen.findByLabelText("Upload training file");
  fireEvent.change(input, { target: { files: [new File(["a,b\n1,2"], "ride.csv", { type: "text/csv" })] } });
  expect(await screen.findByText("Upload or processing failed. The file was not imported.")).toBeInTheDocument();
  expect(screen.queryByText("raw database failure")).not.toBeInTheDocument();
});

it("shows an understandable duplicate upload message", async () => {
  vi.mocked(uploadImport).mockRejectedValue(
    new ApiError("This file was already uploaded", 409, "duplicate_import"),
  );
  render(<IntegrationManager />);
  const input = await screen.findByLabelText("Upload training file");
  fireEvent.change(input, {
    target: { files: [new File(["a,b\n1,2"], "ride.csv", { type: "text/csv" })] },
  });
  expect(await screen.findByText(/already imported/)).toBeInTheDocument();
});

it("renders a useful provider-load error and retry action", async () => {
  vi.mocked(getProviders).mockRejectedValue(new Error("offline"));
  render(<IntegrationManager />);
  expect(await screen.findByRole("alert")).toHaveTextContent("could not load");
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
});
