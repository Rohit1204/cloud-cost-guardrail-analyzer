import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AlertRunner } from "@/components/AlertRunner";
import { alertRunFixture } from "@/test/fixtures";

describe("AlertRunner", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("runs alerts and shows delivery status", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(alertRunFixture)));
    const user = userEvent.setup();

    render(<AlertRunner months={6} />);

    await user.type(screen.getByPlaceholderText("you@example.com"), "owner@example.com");
    await user.click(screen.getByRole("button", { name: /run alert workflow/i }));

    await waitFor(() => expect(screen.getByText("delivered")).toBeInTheDocument());
    expect(screen.getByText("1 recommendations sent")).toBeInTheDocument();
  });

  it("shows alert API errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: "gmail failed" }), { status: 500 }));
    const user = userEvent.setup();

    render(<AlertRunner months={1} />);

    await user.click(screen.getByRole("button", { name: /run alert workflow/i }));

    await waitFor(() => expect(screen.getByText("gmail failed")).toBeInTheDocument());
  });
});
