export interface I18nText {
  en_US: string
  zh_Hans: string
}

export interface PluginVerification {
  authorized_category: string
}

export interface PluginResource {
  memory: number
}

export interface Plugin {
  type: string
  name: string
  org: string
  plugin_id: string
  icon: string
  label: I18nText
  brief: I18nText
  introduction: string
  category: string
  created_at: string
  updated_at: string
  install_count: number
  latest_version: string
  latest_package_identifier: string
  status: string
  tags: string[]
  verification: PluginVerification | null
  badges: Record<string, unknown>[]
  repository: string | null
  resource: PluginResource | null
  privacy_policy: string
}

export interface SearchParams {
  keyword: string
  category: string
  page: number
  page_size: number
}

export interface SearchResult {
  plugins: Plugin[]
  total: number
}

export interface Collection {
  name: string
  label: I18nText
  description: I18nText
  searchable: boolean
  search_params: Record<string, unknown>
  priority: number
}

export interface CollectionsResult {
  collections: Collection[]
  total: number
}

export interface BatchParams {
  plugin_ids: string[]
}

export interface BatchResult {
  plugins: Plugin[]
}

export interface ApiError {
  status: number
  message: string
  details?: unknown
}
