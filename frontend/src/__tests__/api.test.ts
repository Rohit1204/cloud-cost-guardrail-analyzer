import { afterEach, describe, expect, it, vi } from "vitest";
import { getCostSummary, getHealth, runAlerts, updateRecommendationStatus } from "@/lib/api";
import { clearAuthSession, storeAuthSession } from "@/lib/auth";
import { alertRunFixture, costSummaryFixture, healthFixture } from "@/test/fixtures";

describe("api client", () => {
  afterEach(() => {
    clearAuthSession();
    vi.restoreAllMocks();
  });

  it("loads health from the configured API", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(healthFixture)));

    await expect(getHealth()).resolves.toEqual(healthFixture);
    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/health", expect.objectContaining({ headers: expect.any(Object) }));
  });

  it("loads cost summary with months query", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(costSummaryFixture)));

    await expect(getCostSummary(6)).resolves.toEqual(costSummaryFixture);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/costs/summary?months=6"), expect.any(Object));
  });

  it("adds Google ID token when signed in", async () => {
    storeAuthSession("signed-token", { email: "owner@example.com" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(healthFixture)));

    await getHealth();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/health"),
      expect.objectContaining({
        headers: expect.objectContaining({ authorization: "Bearer signed-token" }),
      }),
    );
  });

  it("posts alert run payload", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(alertRunFixture)));

    await expect(runAlerts({ cost_months: 3, alert_channels: ["gmail"], gmail_recipient: "you@example.com" })).resolves.toEqual(alertRunFixture);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/alerts/run"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ cost_months: 3, alert_channels: ["gmail"], gmail_recipient: "you@example.com" }),
      }),
    );
  });

  it("patches recommendation status", async () => {
    const payload = { recommendation_id: "rec-001", status: "acknowledged" as const, updated_at: "2026-04-29T00:00:00Z" };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(payload)));

    await expect(updateRecommendationStatus({ recommendation_id: "rec-001", status: "acknowledged" })).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recommendations/status"),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ recommendation_id: "rec-001", status: "acknowledged" }),
      }),
    );
  });

  it("throws useful API errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: "bad months" }), { status: 400 }));

    await expect(getCostSummary(24)).rejects.toThrow("bad months");
  });
});
