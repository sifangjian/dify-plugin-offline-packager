export interface I18nText {
  en_US: string
  zh_Hans: string
}

export interface UploadResponse {
  upload_id: string
  author: string
  name: string
  version: string
  label: I18nText
  description: I18nText
}

export interface UploadError {
  filename: string
  error: string
}

export interface BatchUploadResponse {
  success: UploadResponse[]
  failed: UploadError[]
}
