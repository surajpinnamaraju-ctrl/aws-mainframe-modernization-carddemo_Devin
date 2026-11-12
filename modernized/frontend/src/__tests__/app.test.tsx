import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

beforeEach(() => { mockFetch.mockReset(); });

describe("App", () => {
  it("renders sign-on screen", () => {
    render(<App />);
    expect(screen.getByText("01 / Sign on")).toBeInTheDocument();
    expect(screen.getByLabelText("User ID")).toBeInTheDocument();
  });

  it("logs in and shows the main menu", async () => {
    mockFetch.mockResolvedValue(json({
      token: "t1", user_id: "USER0001", first_name: "Test",
      last_name: "User", user_type: "U",
    }));
    render(<App />);
    fireEvent.change(screen.getByLabelText("User ID"),
      { target: { value: "USER0001" } });
    fireEvent.change(screen.getByLabelText("Password"),
      { target: { value: "PASSWORD" } });
    fireEvent.click(screen.getByText("Sign in"));
    await waitFor(() =>
      expect(screen.getByText(/Main Menu/)).toBeInTheDocument());
    expect(screen.getByText("Test User · USER0001")).toBeInTheDocument();
    // regular users do not see admin-only items
    expect(screen.queryByText("User Admin")).not.toBeInTheDocument();
  });

  it("admin sees admin menu items", async () => {
    mockFetch.mockResolvedValue(json({
      token: "t2", user_id: "ADMIN001", first_name: "Admin",
      last_name: "One", user_type: "A",
    }));
    render(<App />);
    fireEvent.change(screen.getByLabelText("User ID"),
      { target: { value: "ADMIN001" } });
    fireEvent.change(screen.getByLabelText("Password"),
      { target: { value: "PASSWORD" } });
    fireEvent.click(screen.getByText("Sign in"));
    await waitFor(() =>
      expect(screen.getByText(/Main Menu/)).toBeInTheDocument());
    expect(screen.getByText("User Admin")).toBeInTheDocument();
    expect(screen.getByText("Batch")).toBeInTheDocument();
  });

  it("shows error on bad credentials", async () => {
    mockFetch.mockResolvedValue(
      json({ detail: "Invalid credentials" }, 401));
    render(<App />);
    fireEvent.change(screen.getByLabelText("User ID"),
      { target: { value: "X" } });
    fireEvent.change(screen.getByLabelText("Password"),
      { target: { value: "y" } });
    fireEvent.click(screen.getByText("Sign in"));
    await waitFor(() =>
      expect(screen.getByRole("alert"))
        .toHaveTextContent("Invalid credentials"));
  });
});
