import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LoginGate } from "@/components/LoginGate";
import { clearAuthSession, storeAuthSession } from "@/lib/auth";

vi.mock("@/components/Dashboard", () => ({
  Dashboard: ({ user, onSignOut }: { user: { email: string }; onSignOut: () => void }) => (
    <div>
      <p>Dashboard for {user.email}</p>
      <button onClick={onSignOut} type="button">
        Sign out
      </button>
    </div>
  ),
}));

describe("LoginGate", () => {
  afterEach(() => {
    clearAuthSession();
    vi.restoreAllMocks();
  });

  it("shows local development login when Google client id is not configured", async () => {
    const user = userEvent.setup();
    render(<LoginGate />);

    await user.click(screen.getByRole("button", { name: /continue in local development/i }));

    expect(screen.getByText("Dashboard for local-dev@example.com")).toBeInTheDocument();
  });

  it("restores an existing signed-in user", () => {
    storeAuthSession("token", { email: "owner@example.com" });

    render(<LoginGate />);

    expect(screen.getByText("Dashboard for owner@example.com")).toBeInTheDocument();
  });
});
