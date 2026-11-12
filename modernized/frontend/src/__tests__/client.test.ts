import { api, fmtMoney, setToken } from "../api/client";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
  setToken(null);
});

describe("api client", () => {
  it("sends JSON with auth header when token set", async () => {
    setToken("abc");
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await api("/api/health");
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/health");
    expect(init.headers.Authorization).toBe("Bearer abc");
    expect(init.headers["Content-Type"]).toBe("application/json");
  });

  it("returns parsed body", async () => {
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ a: 1 }), { status: 200 }));
    expect(await api("/x")).toEqual({ a: 1 });
  });

  it("throws ApiError with detail on failure", async () => {
    mockFetch.mockResolvedValue(new Response(
      JSON.stringify({ detail: "Bad credentials" }), { status: 401 }));
    await expect(api("/x")).rejects.toMatchObject(
      { name: "ApiError", status: 401, message: "Bad credentials" });
  });

  it("serializes body for POST", async () => {
    mockFetch.mockResolvedValue(
      new Response("{}", { status: 201 }));
    await api("/x", { method: "POST", body: { n: 1 } });
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({ n: 1 });
  });
});

describe("fmtMoney", () => {
  it("formats with two decimals and dollar sign", () => {
    expect(fmtMoney("42.5")).toBe("$42.50");
    expect(fmtMoney(0)).toBe("$0.00");
    expect(fmtMoney("194.00")).toBe("$194.00");
  });
});
