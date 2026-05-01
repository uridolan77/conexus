import { afterEach, describe, expect, it } from "vitest";
import {
  setPlaygroundApiKeyOnce,
  takePlaygroundApiKeyOnce,
} from "@/lib/playgroundKeyHandoff";

afterEach(() => {
  takePlaygroundApiKeyOnce(); // drain any leftover state between tests
});

describe("playgroundKeyHandoff", () => {
  it("set then take returns the key", () => {
    setPlaygroundApiKeyOnce("cx_live_testkey");
    expect(takePlaygroundApiKeyOnce()).toBe("cx_live_testkey");
  });

  it("second take returns null", () => {
    setPlaygroundApiKeyOnce("cx_live_testkey");
    takePlaygroundApiKeyOnce();
    expect(takePlaygroundApiKeyOnce()).toBeNull();
  });

  it("take without prior set returns null", () => {
    expect(takePlaygroundApiKeyOnce()).toBeNull();
  });

  it("blank key is not stored", () => {
    setPlaygroundApiKeyOnce("   ");
    expect(takePlaygroundApiKeyOnce()).toBeNull();
  });

  it("empty string is not stored", () => {
    setPlaygroundApiKeyOnce("");
    expect(takePlaygroundApiKeyOnce()).toBeNull();
  });

  it("second set overwrites the first", () => {
    setPlaygroundApiKeyOnce("cx_live_first");
    setPlaygroundApiKeyOnce("cx_live_second");
    expect(takePlaygroundApiKeyOnce()).toBe("cx_live_second");
  });
});
