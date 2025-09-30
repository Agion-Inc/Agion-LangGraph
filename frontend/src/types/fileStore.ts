/**
 * Complete File Store Type Definitions
 * Properly typed for all file management operations
 */

import { FileStatus, UploadedFile, FileInfo, WorksheetData } from './files'

export interface FileStoreState {
  files: UploadedFile[]
  isUploading: boolean
  isLoading: boolean
  uploadProgress: Record<string, number>
  error: string | null
  totalSize: number
  maxFileSize: number
  allowedTypes: string[]
}

export interface FileStoreActions {
  // Core operations
  loadFiles: () => Promise<void>
  uploadFiles: (files: File[]) => Promise<UploadedFile[]>
  removeFile: (fileId: string) => Promise<void>
  
  // Local operations
  renameFile: (fileId: string, newName: string) => void
  clearFiles: () => void
  updateFileStatus: (fileId: string, status: FileStatus, progress?: number) => void
  setError: (error: string | null) => void
  
  // Advanced operations
  retryUpload: (fileId: string) => Promise<void>
  getFileInfo: (fileId: string) => Promise<FileInfo>
  getWorksheetData: (fileId: string, worksheetId: string, limit?: number, offset?: number) => Promise<WorksheetData>
}

export type CompleteFileStore = FileStoreState & FileStoreActions
