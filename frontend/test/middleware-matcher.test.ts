import { describe, expect, it } from "vitest";
import { shouldProtectPathname } from "../middleware";

describe("shouldProtectPathname", () => {
  it("skips Next internals, API routes, favicon, and login", () => {
    expect(shouldProtectPathname("/_next/static/chunk.js")).toBe(false);
    expect(shouldProtectPathname("/_next/image")).toBe(false);
    expect(shouldProtectPathname("/api/foo")).toBe(false);
    expect(shouldProtectPathname("/favicon.ico")).toBe(false);
    expect(shouldProtectPathname("/login")).toBe(false);
    expect(shouldProtectPathname("/login/callback")).toBe(false);
  });

  it("protects BO app routes including adaptation", () => {
    expect(shouldProtectPathname("/")).toBe(true);
    expect(shouldProtectPathname("/adaptation")).toBe(true);
    expect(shouldProtectPathname("/adaptation/plans")).toBe(true);
    expect(shouldProtectPathname("/requests")).toBe(true);
    expect(shouldProtectPathname("/loginfo")).toBe(true);
  });
});
