import { afterEach, describe, expect, it, vi } from "vitest";
import { getCostSummary, getHealth, runAlerts } from "@/lib/api";
import { alertRunFixture, costSummaryFixture, healthFixture } from "@/test/fixtures";

describe("api client", () => {
  afterEach(() => {
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

  it("throws useful API errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: "bad months" }), { status: 400 }));

    await expect(getCostSummary(24)).rejects.toThrow("bad months");
  });
});
