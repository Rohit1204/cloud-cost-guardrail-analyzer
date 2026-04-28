import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RecommendationsList } from "@/components/RecommendationsList";
import { recommendationsFixture } from "@/test/fixtures";

describe("RecommendationsList", () => {
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
});
