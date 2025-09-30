/**
 * Agent-Chat Simple File Manager Page
 * Complete file management without AnimatePresence
 */

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  DocumentIcon,
  EyeIcon,
  TrashIcon,
  CloudArrowUpIcon,
  MagnifyingGlassIcon,
  ArrowDownTrayIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import { useFileStore } from '../hooks/useFiles'
import { FilesChatInput } from '../components/chat/FilesChatInput'
import toast from 'react-hot-toast'

export const FileManagerPage: React.FC = () => {
  const { files, removeFile, renameFile, loadFiles, isLoading } = useFileStore()
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [editingFileId, setEditingFileId] = useState<string | null>(null)
  const [editingFileName, setEditingFileName] = useState<string>('')

  // Load files when component mounts
  useEffect(() => {
    console.log('[FileManagerPage] Loading files on mount...')
    loadFiles().catch(error => {
      console.error('[FileManagerPage] Failed to load files:', error)
      toast.error('Failed to load files')
    })
  }, [])

  const handleStartRename = (fileId: string, currentName: string) => {
    setEditingFileId(fileId)
    setEditingFileName(currentName)
  }

  const handleFinishRename = (fileId: string) => {
    if (editingFileName.trim() && editingFileName !== files.find(f => f.id === fileId)?.name) {
      renameFile(fileId, editingFileName.trim())
    }
    setEditingFileId(null)
    setEditingFileName('')
  }

  const handleCancelRename = () => {
    setEditingFileId(null)
    setEditingFileName('')
  }

  const handleDeleteFile = async (fileId: string) => {
    if (!window.confirm('Are you sure you want to delete this file?')) {
      return
    }

    try {
      // Use the store's removeFile which handles both API call and state update
      await removeFile(fileId)
      toast.success('File deleted successfully')

      // Optionally reload files to ensure sync with backend
      // await loadFiles()
    } catch (error) {
      // Check if it's a 404 error (file already deleted)
      if (error instanceof Error && error.message.includes('404')) {
        // File was already deleted, just reload the list
        toast.success('File removed')
        await loadFiles()
      } else {
        toast.error('Failed to delete file')
        console.error('Error deleting file:', error)
      }
    }
  }

  const handleDownloadFile = async (fileId: string, filename: string) => {
    try {
      const response = await fetch(`/api/v1/files/${fileId}/download`)
      if (!response.ok) throw new Error('Failed to download file')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      toast.success('File downloaded successfully')
    } catch (error) {
      toast.error('Failed to download file')
      console.error('Error downloading file:', error)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getFileIcon = (category: string) => {
    switch (category) {
      case 'excel':
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

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      processed: { color: 'green', icon: '✓', label: 'Processed' },
      completed: { color: 'green', icon: '✓', label: 'Completed' },
      uploaded: { color: 'blue', icon: '📤', label: 'Uploaded' },
      processing: { color: 'yellow', icon: '⚙️', label: 'Processing' },
      error: { color: 'red', icon: '❌', label: 'Error' },
    }

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.uploaded

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-${config.color}-100 text-${config.color}-800`}>
        {config.icon} {config.label}
      </span>
    )
  }

  // Filter files based on search
  const filteredFiles = files.filter(file =>
    file.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full">
      {/* Files Content Area */}
      <div className="flex-1 overflow-y-auto bg-gray-50">
        {/* Search Header */}
        <div className="bg-white shadow-sm border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-4 flex-1">
                <MagnifyingGlassIcon className="w-5 h-5 text-gray-400 flex-shrink-0" />
                <input
                  type="text"
                  placeholder="Search files..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 max-w-2xl border-none focus:outline-none focus:ring-0 text-gray-900 placeholder-gray-500 text-base"
                />
                <span className="text-sm text-gray-500 whitespace-nowrap">
                  {filteredFiles.length} file{filteredFiles.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Files List */}
        <div className="bg-white rounded-lg shadow">
          {loading ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading files...</p>
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="p-8 text-center">
              <DocumentIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {searchTerm ? 'No files found' : 'No files uploaded'}
              </h3>
              <p className="text-gray-600">
                {searchTerm 
                  ? 'Try adjusting your search term'
                  : 'Upload your first file to get started'
                }
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredFiles.map((file) => (
                <motion.div
                  key={file.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-6 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 flex-1 min-w-0">
                      <div className="text-3xl flex-shrink-0">
                        {getFileIcon('excel')}
                      </div>
                      <div className="flex-1 min-w-0">
                        {editingFileId === file.id ? (
                          <input
                            type="text"
                            value={editingFileName}
                            onChange={(e) => setEditingFileName(e.target.value)}
                            onBlur={() => handleFinishRename(file.id)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                handleFinishRename(file.id)
                              } else if (e.key === 'Escape') {
                                handleCancelRename()
                              }
                            }}
                            autoFocus
                            className="w-full text-lg font-medium text-gray-900 bg-white border border-blue-500 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        ) : (
                          <h4 
                            className="text-lg font-medium text-gray-900 truncate cursor-pointer hover:text-blue-600 transition-colors"
                            onClick={() => handleStartRename(file.id, file.name)}
                            title="Click to rename file"
                          >
                            {file.name}
                          </h4>
                        )}
                        <div className="flex items-center space-x-4 mt-1">
                          <span className="text-sm text-gray-500">
                            {formatFileSize(file.size)}
                          </span>
                          <span className="text-sm text-gray-500">
                            {file.uploadedAt?.toLocaleDateString() || 'Unknown date'}
                          </span>
                          {getStatusBadge(file.status)}
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center space-x-2 flex-shrink-0">
                      <button
                        onClick={() => handleDownloadFile(file.id, file.name)}
                        className="p-2 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        title="Download file"
                      >
                        <ArrowDownTrayIcon className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDeleteFile(file.id)}
                        className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete file"
                      >
                        <TrashIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

          {/* Footer */}
          <div className="mt-8 text-center text-sm text-gray-500">
            <p>💡 Tip: Files with "completed" status can be referenced in chat using @filename</p>
          </div>
        </div>
      </div>

      {/* Chat Input Area - Always at bottom */}
      <FilesChatInput />
    </div>
  )
}

export default FileManagerPage
