/**
 * Agent-Chat File Manager Component
 * Complete file management with upload, list, and data viewing
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { DocumentIcon, EyeIcon, TrashIcon, CloudArrowUpIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { useFileStore } from '../../hooks/useFiles'
import { FileUploadZone } from '../upload/FileDropZone'
import FileDataViewer from './FileDataViewer'
import type { UploadedFile } from '../../types/files'

export const FileManager: React.FC = () => {
  const { files, removeFile } = useFileStore()
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [showUpload, setShowUpload] = useState(true)
  const [deletingFiles, setDeletingFiles] = useState<Set<string>>(new Set())

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase()
    switch (extension) {
      case 'xlsx':
      case 'xls':
        return '📊'
      case 'csv':
        return '📝'
      case 'json':
        return '🔧'
      case 'parquet':
        return '📋'
      default:
        return '📄'
    }
  }

  const getStatusBadge = (status: UploadedFile['status']) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            ✓ Processed
          </span>
        )
      case 'uploading':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            ⏳ Uploading
          </span>
        )
      case 'processing':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            ⚙️ Processing
          </span>
        )
      case 'error':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            ❌ Error
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            ⏸️ Pending
          </span>
        )
    }
  }

  const completedFiles = files.filter(f => f.status === 'completed')

  return (
    <div className="h-full flex flex-col">
      {/* File Data Viewer - Full Screen */}
      {selectedFileId && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="w-full max-w-6xl h-full max-h-screen overflow-hidden"
          >
            <FileDataViewer
              fileId={selectedFileId}
              onClose={() => setSelectedFileId(null)}
            />
          </motion.div>
        </motion.div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-chat-gray-200">
        <h2 className="text-lg font-semibold text-chat-gray-900">File Manager</h2>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center space-x-2 px-3 py-2 text-sm font-medium text-chat-blue-600 hover:text-chat-blue-700 bg-chat-blue-50 hover:bg-chat-blue-100 rounded-lg transition-colors"
        >
          <CloudArrowUpIcon className="w-4 h-4" />
          <span>{showUpload ? 'Hide Upload' : 'Show Upload'}</span>
        </button>
      </div>

      {/* Upload Section */}
      {showUpload && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="overflow-hidden"
        >
          <div className="p-4 border-b border-chat-gray-200">
            <FileUploadZone />
          </div>
        </motion.div>
      )}

      {/* Files List */}
      <div className="flex-1 overflow-y-auto">
        {files.length === 0 ? (
          <div className="p-8 text-center">
            <DocumentIcon className="w-12 h-12 text-chat-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-chat-gray-900 mb-2">No files uploaded</h3>
            <p className="text-chat-gray-600">
              Upload your first Excel, CSV, or JSON file to get started
            </p>
          </div>
        ) : (
          <div className="divide-y divide-chat-gray-200">
            {files.map((file) => (
              <motion.div
                key={file.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 hover:bg-chat-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <div className="text-2xl flex-shrink-0">
                      {getFileIcon(file.name)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-chat-gray-900 truncate">
                        {file.name}
                      </h4>
                      <div className="flex items-center space-x-3 mt-1">
                        <span className="text-xs text-chat-gray-500">
                          {formatFileSize(file.size)}
                        </span>
                        <span className="text-xs text-chat-gray-500">
                          {file.uploadedAt.toLocaleDateString()}
                        </span>
                        {getStatusBadge(file.status)}
                      </div>
                      {file.progress !== undefined && file.progress < 100 && file.status === 'uploading' && (
                        <div className="mt-2">
                          <div className="bg-chat-gray-200 rounded-full h-1.5">
                            <div
                              className="bg-chat-blue-600 h-1.5 rounded-full transition-all duration-300"
                              style={{ width: `${file.progress}%` }}
                            />
                          </div>
                          <span className="text-xs text-chat-gray-500 mt-1">
                            {file.progress}% uploaded
                          </span>
                        </div>
                      )}
                      {file.error && (
                        <p className="text-xs text-red-600 mt-1">{file.error}</p>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2 flex-shrink-0">
                    {file.status === 'completed' && (
                      <button
                        onClick={() => setSelectedFileId(file.id)}
                        className="p-2 text-chat-gray-500 hover:text-chat-blue-600 hover:bg-chat-blue-50 rounded-lg transition-colors"
                        title="View data"
                      >
                        <EyeIcon className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={async () => {
                        setDeletingFiles(prev => new Set(prev).add(file.id))
                        try {
                          await removeFile(file.id)
                        } catch (error) {
                          console.error('Failed to delete file:', error)
                          // Optionally show a toast/notification here
                        } finally {
                          setDeletingFiles(prev => {
                            const next = new Set(prev)
                            next.delete(file.id)
                            return next
                          })
                        }
                      }}
                      disabled={deletingFiles.has(file.id)}
                      className={`p-2 rounded-lg transition-colors ${
                        deletingFiles.has(file.id)
                          ? 'text-chat-gray-300 cursor-not-allowed'
                          : 'text-chat-gray-500 hover:text-red-600 hover:bg-red-50'
                      }`}
                      title={deletingFiles.has(file.id) ? "Deleting..." : "Remove file"}
                    >
                      {deletingFiles.has(file.id) ? (
                        <div className="w-4 h-4 border-2 border-chat-gray-300 border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <TrashIcon className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Quick Stats */}
        {completedFiles.length > 0 && (
          <div className="p-4 bg-chat-gray-50 border-t border-chat-gray-200">
            <div className="text-sm text-chat-gray-600">
              <div className="flex justify-between items-center">
                <span>
                  {completedFiles.length} file{completedFiles.length !== 1 ? 's' : ''} ready for analysis
                </span>
                <span>
                  Total size: {formatFileSize(completedFiles.reduce((sum, f) => sum + f.size, 0))}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default FileManager