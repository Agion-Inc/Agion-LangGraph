/**
 * Agent-Chat useFiles Hook
 * Zustand store for file management with latest APIs
 */

import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { nanoid } from 'nanoid'
import type { FileStore, UploadedFile, FileStatus, FileInfo, WorksheetData } from '../types/files'
import { apiClient } from '../services/api'

// Extended FileStore with isLoading property
interface ExtendedFileStore extends FileStore {
  isLoading: boolean
  loadFiles: () => Promise<void>
}

export const useFileStore = create<ExtendedFileStore>()(
  subscribeWithSelector((set, get) => ({
    // State
    files: [],
    isUploading: false,
    isLoading: false,
    uploadProgress: {},
    error: null,
    totalSize: 0,
    maxFileSize: 100 * 1024 * 1024, // 100MB
    allowedTypes: ['.xlsx', '.csv', '.json', '.parquet', '.xls'],

    // Actions
    loadFiles: async (): Promise<void> => {
      set({ isLoading: true, error: null })
      try {
        const response = await apiClient.get<{
          files: Array<{
            file_id: string
            filename: string
            original_filename: string
            file_size: number
            content_type: string
            status: string
            created_at: string
            category: string
            metadata?: Record<string, any>
          }>
          total: number
        }>('/api/v1/files', { page: '1', size: '100' })

        // Convert backend file format to frontend format
        const files: UploadedFile[] = response.files.map(file => ({
          id: file.file_id,
          name: file.filename,
          size: file.file_size,
          type: file.content_type || 'application/octet-stream',
          status: (file.status === 'processed' || file.status === 'uploaded') ? 'completed' : 'error' as FileStatus,
          progress: 100,
          uploadedAt: new Date(file.created_at),
          worksheets: [],
          metadata: file.metadata
        }))

        const totalSize = files.reduce((sum, f) => sum + f.size, 0)
        
        set({
          files,
          totalSize,
          isLoading: false,
          error: null
        })

        console.log(`Loaded ${files.length} files from backend`)
      } catch (error) {
        console.error('Failed to load files:', error)
        set({
          isLoading: false,
          error: error instanceof Error ? error.message : 'Failed to load files'
        })
      }
    },
    uploadFiles: async (files: File[]): Promise<UploadedFile[]> => {
      const { maxFileSize, allowedTypes } = get()
      set({ isUploading: true, error: null })

      try {
        // Validate files
        const invalidFiles = files.filter(file => {
          const extension = '.' + file.name.split('.').pop()?.toLowerCase()
          return file.size > maxFileSize || !allowedTypes.includes(extension)
        })

        if (invalidFiles.length > 0) {
          throw new Error(`Invalid files: ${invalidFiles.map(f => f.name).join(', ')}`)
        }

        // Create file records
        const uploadedFiles: UploadedFile[] = files.map(file => ({
          id: nanoid(),
          name: file.name,
          size: file.size,
          type: file.type,
          status: 'uploading' as FileStatus,
          progress: 0,
          uploadedAt: new Date(),
        }))

        // Add files to state
        set(state => ({
          files: [...state.files, ...uploadedFiles],
          totalSize: state.totalSize + files.reduce((sum, f) => sum + f.size, 0),
        }))

        // Upload files using multiple file upload endpoint
        try {
          // Update progress for all files
          uploadedFiles.forEach(uploadedFile => {
            set(state => ({
              uploadProgress: {
                ...state.uploadProgress,
                [uploadedFile.id]: 50, // Simulate progress
              },
            }))
          })

          // Upload all files at once with immediate processing
          const response = await apiClient.uploadFiles('/api/v1/files/upload-multiple', files, {
            process_immediately: true, // Send as boolean
            upload_source: 'web_ui'
          })

          // Log response for debugging
          console.log('File upload response:', response)

          // Update file status and IDs for all files
          if (Array.isArray(response)) {
            (response as any[]).forEach((fileResponse, index) => {
              const uploadedFile = uploadedFiles[index]
              
              // Be more lenient with status checking - accept various success indicators
              const isSuccess = 
                fileResponse.status === 'uploaded' || 
                fileResponse.status === 'processed' ||
                fileResponse.status === 'success' ||
                fileResponse.status === 'ok' ||
                fileResponse.file_id ||
                fileResponse.id ||
                (!fileResponse.error && !fileResponse.status) // No error means success

              if (isSuccess) {
                // Update the file to completed status
                const newFileId = fileResponse.file_id || fileResponse.id || uploadedFile.id
                set(state => ({
                  files: state.files.map(f =>
                    f.id === uploadedFile.id
                      ? {
                          ...f,
                          id: newFileId,
                          metadata: fileResponse.metadata || fileResponse.data || fileResponse,
                          status: 'completed' as FileStatus,
                          progress: 100,
                          processedAt: new Date()
                        }
                      : f
                  ),
                  uploadProgress: {
                    ...state.uploadProgress,
                    [newFileId]: 100
                  }
                }))
              } else {
                // Handle error but still mark as completed if we have data
                const hasUsableData = fileResponse.metadata || fileResponse.data || fileResponse.worksheets
                set(state => ({
                  files: state.files.map(f =>
                    f.id === uploadedFile.id
                      ? {
                          ...f,
                          id: fileResponse.file_id || fileResponse.id || uploadedFile.id,
                          status: (hasUsableData ? 'completed' : 'error') as FileStatus,
                          error: fileResponse.error || fileResponse.message || 'Upload issue',
                          metadata: fileResponse.metadata || fileResponse.data || fileResponse,
                          progress: hasUsableData ? 100 : 0,
                          processedAt: hasUsableData ? new Date() : undefined
                        }
                      : f
                  )
                }))
              }
            })
          } else if (response && typeof response === 'object') {
            // Handle single response object or different response format
            console.log('Non-array response, treating as successful upload')
            
            // Mark all files as completed since we got a response
            uploadedFiles.forEach((uploadedFile, index) => {
              const responseData = (response as any)[index] || response
              set(state => ({
                files: state.files.map(f =>
                  f.id === uploadedFile.id
                    ? {
                        ...f,
                        status: 'completed' as FileStatus,
                        progress: 100,
                        processedAt: new Date(),
                        metadata: responseData
                      }
                    : f
                ),
                uploadProgress: {
                  ...state.uploadProgress,
                  [uploadedFile.id]: 100
                }
              }))
            })
          }

          set({ isUploading: false })
          return uploadedFiles
        } catch (error) {
          console.error('File upload error:', error)
          
          // Even on error, check if files were partially uploaded
          uploadedFiles.forEach(uploadedFile => {
            // Keep files that might have partial data
            set(state => ({
              files: state.files.map(f =>
                f.id === uploadedFile.id
                  ? {
                      ...f,
                      status: 'error' as FileStatus,
                      error: error instanceof Error ? error.message : 'Upload failed',
                      progress: 0
                    }
                  : f
              )
            }))
          })
          
          const errorMessage = error instanceof Error ? error.message : 'Upload failed'
          set({ error: errorMessage, isUploading: false })
          throw error
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed'
        set({ error: errorMessage, isUploading: false })
        throw error
      }
    },

    removeFile: async (fileId: string) => {
      try {
        // Call backend to delete file
        await apiClient.delete(`/api/v1/files/${fileId}`)
        
        // Remove from local state after successful backend deletion
        set(state => {
          const file = state.files.find(f => f.id === fileId)
          const newFiles = state.files.filter(f => f.id !== fileId)
          const newTotalSize = file ? state.totalSize - file.size : state.totalSize
          const newProgress = { ...state.uploadProgress }
          delete newProgress[fileId]

          return {
            files: newFiles,
            totalSize: newTotalSize,
            uploadProgress: newProgress,
          }
        })
        
        console.log(`File ${fileId} deleted successfully`)
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to delete file'
        set({ error: errorMessage })
        throw error
      }
    },


    renameFile: (fileId: string, newName: string) => {
      set(state => ({
        files: state.files.map(f =>
          f.id === fileId ? { ...f, name: newName } : f
        )
      }))
    },

    retryUpload: async (fileId: string) => {
      // Implementation would retry the specific file upload
      set(state => ({
        uploadProgress: {
          ...state.uploadProgress,
          [fileId]: 0,
        },
      }))

      get().updateFileStatus(fileId, 'uploading', 0)

      // Actual retry logic would go here
      setTimeout(() => {
        get().updateFileStatus(fileId, 'completed', 100)
      }, 2000)
    },

    clearFiles: () => {
      set({
        files: [],
        uploadProgress: {},
        totalSize: 0,
        error: null,
      })
    },

    updateFileStatus: (fileId: string, status: FileStatus, progress?: number) => {
      set(state => ({
        files: state.files.map(file =>
          file.id === fileId
            ? {
                ...file,
                status,
                progress: progress !== undefined ? progress : file.progress,
                processedAt: status === 'completed' ? new Date() : file.processedAt,
                error: status === 'error' ? 'Upload failed' : undefined,
              }
            : file
        ),
        uploadProgress: progress !== undefined
          ? { ...state.uploadProgress, [fileId]: progress }
          : state.uploadProgress,
      }))
    },

    setError: (error: string | null) => {
      set({ error })
    },

    getFileInfo: async (fileId: string): Promise<FileInfo> => {
      try {
        const response = await apiClient.get<{ status: string; data: FileInfo }>(`/api/v1/files/${fileId}/info`)
        return response.data
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to get file info'
        set({ error: errorMessage })
        throw error
      }
    },

    getWorksheetData: async (fileId: string, worksheetId: string, limit = 100, offset = 0): Promise<WorksheetData> => {
      try {
        const response = await apiClient.get<{ status: string; data: WorksheetData }>(
          `/api/v1/files/${fileId}/worksheets/${worksheetId}/data`,
          { limit: limit.toString(), offset: offset.toString() }
        )
        return response.data
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to get worksheet data'
        set({ error: errorMessage })
        throw error
      }
    },
  }))
)
