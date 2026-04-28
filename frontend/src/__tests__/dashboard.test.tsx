import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  const user = { email: "owner@example.com", name: "Owner" };

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders dashboard metrics and recommendations", async () => {
    const fetchMock = mockDashboardFetch();

    render(<Dashboard onSignOut={vi.fn()} user={user} />);

    expect(screen.getByText("Cloud cost guardrail dashboard")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("$12.34").length).toBeGreaterThan(0));
    expect(screen.getByText("Invoice estimate")).toBeInTheDocument();
    expect(screen.getByText("Projected month-end")).toBeInTheDocument();
    expect(screen.getByText("Unattached EBS volume: vol-001")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /live data/i })).toBeInTheDocument();
    expect(screen.queryByText("ap-south-1")).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("/health"), expect.any(Object));
  });

  it("checks integration readiness only when requested", async () => {
    const fetchMock = mockDashboardFetch();
    const userEventSession = userEvent.setup();

    render(<Dashboard onSignOut={vi.fn()} user={user} />);
    await waitFor(() => expect(screen.getAllByText("$12.34").length).toBeGreaterThan(0));
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("/health"), expect.any(Object));

    await userEventSession.click(screen.getByRole("button", { name: /check integrations/i }));

    await waitFor(() => expect(screen.getByText("Gmail token: Configured")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/health"), expect.any(Object));
  });

  it("renders loading state before data arrives", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => undefined));

    render(<Dashboard onSignOut={vi.fn()} user={user} />);

    expect(screen.getByText("Loading cost summary")).toBeInTheDocument();
    expect(screen.getByText("Loading recommendations")).toBeInTheDocument();
  });
});
