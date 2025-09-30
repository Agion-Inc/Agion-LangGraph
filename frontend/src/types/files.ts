/**
 * Agent-Chat Frontend Types - File System
 * Type definitions for file upload and management
 */

export type FileStatus = 'pending' | 'uploading' | 'processing' | 'completed' | 'error'

export interface UploadedFile {
  id: string
  name: string
  size: number
  type: string
  status: FileStatus
  progress: number
  uploadedAt: Date
  processedAt?: Date
  url?: string
  metadata?: Record<string, any>
  error?: string
}

export interface FileProcessingResult {
  file_id: string
  status: 'success' | 'error'
  data?: Record<string, any>
  error?: string
  processing_time: number
  agent_results?: Record<string, any>
}

export interface FileUploadProgress {
  file_id: string
  progress: number
  status: FileStatus
  message?: string
}

export interface FileState {
  files: UploadedFile[]
  isUploading: boolean
  uploadProgress: Record<string, number>
  error: string | null
  totalSize: number
  maxFileSize: number
  allowedTypes: string[]
}

export interface FileActions {
  uploadFiles: (files: File[]) => Promise<UploadedFile[]>
  removeFile: (fileId: string) => void
  renameFile: (fileId: string, newName: string) => void
  retryUpload: (fileId: string) => Promise<void>
  clearFiles: () => void
  updateFileStatus: (fileId: string, status: FileStatus, progress?: number) => void
  setError: (error: string | null) => void
  getFileInfo: (fileId: string) => Promise<FileInfo>
  getWorksheetData: (fileId: string, worksheetId: string, limit?: number, offset?: number) => Promise<WorksheetData>
}

export type FileStore = FileState & FileActions

export interface DropZoneState {
  isDragActive: boolean
  isDragAccept: boolean
  isDragReject: boolean
  acceptedFiles: File[]
  rejectedFiles: File[]
}

export interface FilePreview {
  id: string
  name: string
  size: string
  type: string
  icon: string
  color: string
}

export interface WorksheetInfo {
  worksheet_id: string
  sheet_name: string
  sheet_index: number
  row_count: number
  column_count: number
  column_headers: string[]
  data_types: Record<string, string>
}

export interface FileInfo {
  file_id: string
  filename: string
  original_filename: string
  file_size: number
  content_type: string
  status: string
  created_at: string
  processed_at?: string
  metadata: Record<string, any>
  worksheets: WorksheetInfo[]
}

export interface WorksheetRow {
  row_index: number
  data: Record<string, any>
}

export interface WorksheetData {
  worksheet_info: WorksheetInfo
  rows: WorksheetRow[]
  pagination: {
    limit: number
    offset: number
    total_rows: number
    returned_rows: number
  }
}