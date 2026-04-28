import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Dashboard } from "@/components/Dashboard";
import { costSummaryFixture, healthFixture, recommendationsFixture } from "@/test/fixtures";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Line: () => null,
  Bar: () => null,
}));

function mockDashboardFetch() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("/health")) {
      return new Response(JSON.stringify(healthFixture));
    }
    if (url.includes("/costs/summary")) {
      return new Response(JSON.stringify(costSummaryFixture));
    }
    if (url.includes("/recommendations")) {
      return new Response(JSON.stringify(recommendationsFixture));
    }
    return new Response(JSON.stringify({ error: "not found" }), { status: 404 });
  });
}

describe("Dashboard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders dashboard metrics and recommendations", async () => {
    mockDashboardFetch();

    render(<Dashboard />);

    expect(screen.getByText("Cloud cost guardrail dashboard")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("$12.34")).toBeInTheDocument());
    expect(screen.getByText("Unattached EBS volume: vol-001")).toBeInTheDocument();
    expect(screen.getAllByText("ap-south-1").length).toBeGreaterThan(0);
  });

  it("renders loading state before data arrives", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => undefined));

    render(<Dashboard />);

    expect(screen.getByText("Loading cost summary")).toBeInTheDocument();
    expect(screen.getByText("Loading recommendations")).toBeInTheDocument();
  });
});
