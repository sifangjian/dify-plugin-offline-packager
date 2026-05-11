export interface CartItem {
  pluginId: string
  name: string
  org: string
  latestVersion: string
  source: "marketplace" | "local"
}
