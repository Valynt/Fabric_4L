import { expect, test } from "@playwright/test";

import { parseSetCookieHeader } from "./auth-helpers";

test("creates session cookies for frontend and backend hosts", () => {
  const cookies = parseSetCookieHeader(
    "vf_session=session-value; Path=/; HttpOnly; Secure; SameSite=Lax",
    ["app.staging.example.com", "api.staging.example.com"]
  );

  expect(cookies).toEqual([
    expect.objectContaining({
      name: "vf_session",
      value: "session-value",
      domain: "app.staging.example.com",
    }),
    expect.objectContaining({
      name: "vf_session",
      value: "session-value",
      domain: "api.staging.example.com",
    }),
  ]);
});

test("does not duplicate cookies when frontend and backend share a host", () => {
  const cookies = parseSetCookieHeader(
    "vf_session=session-value; Path=/; HttpOnly",
    ["localhost", "localhost"]
  );

  expect(cookies).toHaveLength(1);
  expect(cookies[0].domain).toBe("localhost");
});
