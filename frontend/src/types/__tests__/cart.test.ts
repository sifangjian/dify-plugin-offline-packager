import { describe, it, expect } from "vitest"
import type { CartItem } from "@/types/cart"

describe("CartItem type", () => {
  it("should accept a valid marketplace CartItem", () => {
    const item: CartItem = {
      pluginId: "langgenius/google-search",
      name: "google-search",
      org: "langgenius",
      latestVersion: "1.0.0",
      source: "marketplace",
    }
    expect(item.pluginId).toBe("langgenius/google-search")
    expect(item.name).toBe("google-search")
    expect(item.org).toBe("langgenius")
    expect(item.latestVersion).toBe("1.0.0")
    expect(item.source).toBe("marketplace")
  })

  it("should accept a valid local CartItem", () => {
    const item: CartItem = {
      pluginId: "local/my-plugin",
      name: "my-plugin",
      org: "local",
      latestVersion: "0.1.0",
      source: "local",
    }
    expect(item.source).toBe("local")
  })

  it("should have exactly 5 required fields", () => {
    const item: CartItem = {
      pluginId: "test",
      name: "test",
      org: "test",
      latestVersion: "1.0.0",
      source: "marketplace",
    }
    const keys = Object.keys(item)
    expect(keys).toHaveLength(5)
    expect(keys).toContain("pluginId")
    expect(keys).toContain("name")
    expect(keys).toContain("org")
    expect(keys).toContain("latestVersion")
    expect(keys).toContain("source")
  })
})
