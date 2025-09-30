/**
 * Agent-Chat File Upload Drop Zone
 * Elegant drag-and-drop file upload interface
 */

import React, { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion } from 'framer-motion'
import { CloudArrowUpIcon } from '@heroicons/react/24/outline'
import { useFileStore } from '../../hooks/useFiles'
import toast from 'react-hot-toast'

export const FileUploadZone: React.FC = () => {
  const { uploadFiles, isUploading, maxFileSize, allowedTypes } = useFileStore()

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      try {
        await uploadFiles(acceptedFiles)
        toast.success(`Successfully uploaded ${acceptedFiles.length} file(s)`)
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Upload failed')
      }
    },
    [uploadFiles]
  )

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'application/parquet': ['.parquet'],
    },
    maxSize: maxFileSize,
    disabled: isUploading,
  })

  const getDropZoneClasses = () => {
    let classes = 'file-upload-area cursor-pointer transition-all duration-200 '

    if (isDragActive) {
      classes += isDragAccept ? 'drag-active ' : 'drag-reject '
    }

    if (isUploading) {
      classes += 'opacity-50 cursor-not-allowed '
    }

    return classes
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div
      {...getRootProps()}
      className={getDropZoneClasses()}
    >
      <input {...getInputProps()} />

      <div className="flex flex-col items-center">
        <motion.div
          animate={{
            scale: isDragActive ? 1.1 : 1,
            rotate: isDragActive ? 5 : 0,
          }}
          transition={{ duration: 0.2 }}
        >
          <CloudArrowUpIcon
            className={`w-8 h-8 mb-2 ${
              isDragAccept ? 'text-chat-blue-500' :
              isDragReject ? 'text-red-500' :
              'text-chat-gray-400'
            }`}
          />
        </motion.div>

        <div className="text-center">
          {isUploading ? (
            <div className="text-sm text-chat-gray-600">
              <div className="font-medium">Uploading...</div>
              <div className="text-xs text-chat-gray-500 mt-1">Please wait</div>
            </div>
          ) : isDragActive ? (
            <div className="text-sm text-chat-gray-600">
              {isDragAccept ? (
                <div className="font-medium text-chat-blue-600">Drop files here</div>
              ) : (
                <div className="font-medium text-red-600">Invalid file type</div>
              )}
            </div>
          ) : (
            <div className="text-sm text-chat-gray-600">
              <div className="font-medium">Drop files or click</div>
              <div className="text-xs text-chat-gray-500 mt-1">
                Excel, CSV, JSON up to {formatFileSize(maxFileSize)}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FileUploadZone