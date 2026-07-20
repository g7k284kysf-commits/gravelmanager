import { getPerformanceChart, getPerformanceSummary } from "@/lib/api";

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

it("maps performance requests to authenticated API routes", async () => {
  localStorage.setItem("access_token", "test-token");
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ points: [] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  await getPerformanceChart("180d");
  expect(fetchMock).toHaveBeenCalledWith(
    "http://localhost:8000/api/v1/performance/chart?range=180d",
    expect.objectContaining({
      headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
    }),
  );
});

it("surfaces backend error details for summary requests", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Session expired" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    }),
  );
  await expect(getPerformanceSummary()).rejects.toThrow("Session expired");
});
