import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AlertRunner } from "@/components/AlertRunner";
import { alertRunFixture } from "@/test/fixtures";

describe("AlertRunner", () => {
  const originalAllowedEmails = process.env.NEXT_PUBLIC_ALLOWED_ALERT_EMAILS;

  afterEach(() => {
    vi.restoreAllMocks();
    process.env.NEXT_PUBLIC_ALLOWED_ALERT_EMAILS = originalAllowedEmails;
  });

  it("runs alerts and shows delivery status", async () => {
    process.env.NEXT_PUBLIC_ALLOWED_ALERT_EMAILS = "owner@example.com,team@example.com";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(alertRunFixture)));
    const user = userEvent.setup();

    render(<AlertRunner months={6} />);

    await user.click(screen.getByRole("button", { name: "team@example.com" }));
    await user.click(screen.getByRole("button", { name: /run alert workflow/i }));

    await waitFor(() => expect(screen.getByText("delivered")).toBeInTheDocument());
    expect(screen.getByText("1 recommendations sent")).toBeInTheDocument();
  });

  it("shows alert API errors", async () => {
    process.env.NEXT_PUBLIC_ALLOWED_ALERT_EMAILS = "owner@example.com";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: "gmail failed" }), { status: 500 }));
    const user = userEvent.setup();

    render(<AlertRunner months={1} />);

    await user.click(screen.getByRole("button", { name: /run alert workflow/i }));

    await waitFor(() => expect(screen.getByText("gmail failed")).toBeInTheDocument());
  });

  it("disables Gmail alert runs when no allowed recipients are configured", () => {
    process.env.NEXT_PUBLIC_ALLOWED_ALERT_EMAILS = "";

    render(<AlertRunner months={1} />);

    expect(screen.getByText(/Configure `NEXT_PUBLIC_ALLOWED_ALERT_EMAILS`/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run alert workflow/i })).toBeDisabled();
  });
});
