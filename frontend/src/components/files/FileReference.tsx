/**
 * Agent-Chat File Reference Component
 * Display file references in chat messages with quick access
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { DocumentIcon, EyeIcon, ArrowDownTrayIcon, InformationCircleIcon } from '@heroicons/react/24/outline'
import { useFileStore } from '../../hooks/useFiles'

interface FileReferenceProps {
  fileId: string
  className?: string
  showActions?: boolean
}

export const FileReference: React.FC<FileReferenceProps> = ({
  fileId,
  className = '',
  showActions = true
}) => {
  const [showTooltip, setShowTooltip] = useState(false)
  const { files } = useFileStore()
  
  const file = files.find(f => f.id === fileId)

  if (!file) {
    return (
      <div className={`inline-flex items-center px-2 py-1 bg-red-50 border border-red-200 rounded text-xs text-red-700 ${className}`}>
        <InformationCircleIcon className="w-3 h-3 mr-1" />
        File not found
      </div>
    )
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 border-green-200 text-green-800'
      case 'processing':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      case 'error':
        return 'bg-red-50 border-red-200 text-red-800'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  const handleDownload = async () => {
    try {
      const response = await fetch(`/api/v1/files/${fileId}/download`)
      if (!response.ok) throw new Error('Download failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = file.name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download error:', error)
    }
  }

  return (
    <motion.div
      className={`inline-flex items-center px-3 py-1.5 border rounded-lg text-sm ${getStatusColor(file.status)} ${className}`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span className="text-lg mr-2">{getFileIcon(file.name)}</span>
      
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate max-w-32">{file.name}</div>
        <div className="text-xs opacity-75">
          {formatFileSize(file.size)} • {file.status}
        </div>
      </div>

      {showActions && file.status === 'completed' && (
        <div className="flex items-center space-x-1 ml-2">
          <button
            onClick={handleDownload}
            className="p-1 hover:bg-white/50 rounded transition-colors"
            title="Download file"
          >
            <ArrowDownTrayIcon className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Tooltip */}
      {showTooltip && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute z-50 -top-12 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap"
        >
          {file.name} ({formatFileSize(file.size)})
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-2 border-r-2 border-t-2 border-transparent border-t-gray-900"></div>
        </motion.div>
      )}
    </motion.div>
  )
}

export default FileReference
