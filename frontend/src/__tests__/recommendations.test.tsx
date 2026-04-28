import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RecommendationsList } from "@/components/RecommendationsList";
import { recommendationsFixture } from "@/test/fixtures";

describe("RecommendationsList", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders recommendation details and next steps", () => {
    render(<RecommendationsList recommendations={recommendationsFixture.recommendations} />);

    expect(screen.getByText("Unattached EBS volume: vol-001")).toBeInTheDocument();
    expect(screen.getByText("Snapshot and delete the unattached volume.")).toBeInTheDocument();
    expect(screen.getByText("Create a final snapshot.")).toBeInTheDocument();
    expect(screen.getByText("$8.00")).toBeInTheDocument();
  });

  it("renders an empty state", () => {
    render(<RecommendationsList recommendations={[]} />);

    expect(screen.getByText("No recommendations")).toBeInTheDocument();
  });

  it("filters recommendations by severity and search text", async () => {
    const user = userEvent.setup();
    render(<RecommendationsList recommendations={recommendationsFixture.recommendations} />);

    await user.selectOptions(screen.getByLabelText("Severity filter"), "critical");
    expect(screen.getByText("Idle EC2 instance: i-001")).toBeInTheDocument();
    expect(screen.queryByText("Unattached EBS volume: vol-001")).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Search recommendations"), "no-match");
    expect(screen.getByText("No matching recommendations")).toBeInTheDocument();
  });

  it("updates recommendation status optimistically", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          recommendation_id: "rec-warning-ebs",
          status: "resolved",
          updated_at: "2026-04-29T00:00:00Z",
        }),
      ),
    );
    const user = userEvent.setup();
    render(<RecommendationsList recommendations={recommendationsFixture.recommendations} />);

    await user.click(screen.getAllByRole("button", { name: "Resolved" })[0]);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recommendations/status"),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ recommendation_id: "rec-warning-ebs", status: "resolved" }),
      }),
    );
  });

  it("shows an error when status update fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: "status failed" }), { status: 500 }));
    const user = userEvent.setup();
    render(<RecommendationsList recommendations={recommendationsFixture.recommendations} />);

    await user.click(screen.getAllByRole("button", { name: "Resolved" })[0]);

    expect(await screen.findByText("status failed")).toBeInTheDocument();
  });
});
