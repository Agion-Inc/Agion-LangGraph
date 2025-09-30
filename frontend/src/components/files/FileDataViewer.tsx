/**
 * Agent-Chat File Data Viewer Component
 * Display extracted XLSX data with worksheets and pagination
 */

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { DocumentTextIcon, TableCellsIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { useFileStore } from '../../hooks/useFiles'
import type { FileInfo, WorksheetData, WorksheetInfo } from '../../types/files'

interface FileDataViewerProps {
  fileId: string
  onClose?: () => void
}

export const FileDataViewer: React.FC<FileDataViewerProps> = ({ fileId, onClose }) => {
  const { getFileInfo, getWorksheetData, error } = useFileStore()

  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null)
  const [selectedWorksheet, setSelectedWorksheet] = useState<WorksheetInfo | null>(null)
  const [worksheetData, setWorksheetData] = useState<WorksheetData | null>(null)
  const [loading, setLoading] = useState(false)
  const [currentPage, setCurrentPage] = useState(0)
  const [pageSize] = useState(50)

  useEffect(() => {
    loadFileInfo()
  }, [fileId])

  useEffect(() => {
    if (selectedWorksheet) {
      loadWorksheetData(selectedWorksheet.worksheet_id, currentPage * pageSize, pageSize)
    }
  }, [selectedWorksheet, currentPage])

  const loadFileInfo = async () => {
    try {
      setLoading(true)
      const info = await getFileInfo(fileId)
      setFileInfo(info)

      // Auto-select first worksheet if available
      if (info.worksheets && info.worksheets.length > 0) {
        setSelectedWorksheet(info.worksheets[0])
      }
    } catch (error) {
      console.error('Failed to load file info:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadWorksheetData = async (worksheetId: string, offset: number, limit: number) => {
    try {
      setLoading(true)
      const data = await getWorksheetData(fileId, worksheetId, limit, offset)
      setWorksheetData(data)
    } catch (error) {
      console.error('Failed to load worksheet data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleWorksheetSelect = (worksheet: WorksheetInfo) => {
    setSelectedWorksheet(worksheet)
    setCurrentPage(0)
  }

  const handleNextPage = () => {
    if (worksheetData && (currentPage + 1) * pageSize < worksheetData.worksheet_info.row_count) {
      setCurrentPage(currentPage + 1)
    }
  }

  const handlePrevPage = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1)
    }
  }

  const formatCellValue = (value: any): string => {
    if (value === null || value === undefined) return ''
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  const getDataTypeColor = (dataType: string): string => {
    switch (dataType.toLowerCase()) {
      case 'int64':
      case 'float64':
        return 'text-blue-600 bg-blue-50'
      case 'object':
        return 'text-green-600 bg-green-50'
      case 'datetime64[ns]':
        return 'text-purple-600 bg-purple-50'
      case 'bool':
        return 'text-orange-600 bg-orange-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  if (loading && !fileInfo) {
    return (
      <div className="p-6 text-center">
        <div className="inline-block w-6 h-6 border-2 border-chat-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-2 text-chat-gray-600">Loading file data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 text-center">
        <p className="text-red-600">Error: {error}</p>
        <button
          onClick={loadFileInfo}
          className="mt-2 px-4 py-2 bg-chat-blue-600 text-white rounded hover:bg-chat-blue-700"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!fileInfo) {
    return (
      <div className="p-6 text-center">
        <p className="text-chat-gray-600">No file data available</p>
      </div>
    )
  }

  const totalPages = selectedWorksheet ? Math.ceil(selectedWorksheet.row_count / pageSize) : 0
  const startRow = currentPage * pageSize + 1
  const endRow = Math.min((currentPage + 1) * pageSize, selectedWorksheet?.row_count || 0)

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white rounded-lg shadow-lg overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-chat-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <DocumentTextIcon className="w-6 h-6 text-chat-blue-600" />
            <div>
              <h3 className="text-lg font-semibold text-chat-gray-900">{fileInfo.filename}</h3>
              <p className="text-sm text-chat-gray-600">
                {fileInfo.worksheets.length} sheets • {(fileInfo.file_size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-chat-gray-400 hover:text-chat-gray-600"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Worksheet Tabs */}
      {fileInfo.worksheets.length > 0 && (
        <div className="border-b border-chat-gray-200">
          <div className="flex overflow-x-auto">
            {fileInfo.worksheets.map((worksheet) => (
              <button
                key={worksheet.worksheet_id}
                onClick={() => handleWorksheetSelect(worksheet)}
                className={`flex-shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  selectedWorksheet?.worksheet_id === worksheet.worksheet_id
                    ? 'border-chat-blue-600 text-chat-blue-600 bg-chat-blue-50'
                    : 'border-transparent text-chat-gray-600 hover:text-chat-gray-900 hover:bg-chat-gray-50'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <TableCellsIcon className="w-4 h-4" />
                  <span>{worksheet.sheet_name}</span>
                  <span className="text-xs opacity-75">
                    ({worksheet.row_count} rows)
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Data Content */}
      {selectedWorksheet && (
        <div className="p-4">
          {/* Column Info */}
          <div className="mb-4">
            <h4 className="text-sm font-medium text-chat-gray-900 mb-2">
              Columns ({selectedWorksheet.column_count})
            </h4>
            <div className="flex flex-wrap gap-2">
              {selectedWorksheet.column_headers.map((header, index) => {
                const dataType = selectedWorksheet.data_types[header] || 'unknown'
                return (
                  <span
                    key={index}
                    className={`px-2 py-1 text-xs font-medium rounded-full ${getDataTypeColor(dataType)}`}
                  >
                    {header} ({dataType})
                  </span>
                )
              })}
            </div>
          </div>

          {/* Data Table */}
          {worksheetData && (
            <>
              <div className="overflow-x-auto border border-chat-gray-200 rounded-lg">
                <table className="min-w-full divide-y divide-chat-gray-200">
                  <thead className="bg-chat-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-chat-gray-500 uppercase tracking-wider">
                        Row
                      </th>
                      {selectedWorksheet.column_headers.map((header) => (
                        <th
                          key={header}
                          className="px-3 py-2 text-left text-xs font-medium text-chat-gray-500 uppercase tracking-wider"
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-chat-gray-200">
                    {worksheetData.rows.map((row) => (
                      <tr key={row.row_index} className="hover:bg-chat-gray-50">
                        <td className="px-3 py-2 text-sm text-chat-gray-500 font-mono">
                          {startRow + row.row_index}
                        </td>
                        {selectedWorksheet.column_headers.map((header) => (
                          <td
                            key={header}
                            className="px-3 py-2 text-sm text-chat-gray-900 max-w-xs truncate"
                            title={formatCellValue(row.data[header])}
                          >
                            {formatCellValue(row.data[header])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="mt-4 flex items-center justify-between">
                <div className="text-sm text-chat-gray-600">
                  Showing {startRow} to {endRow} of {selectedWorksheet.row_count} rows
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handlePrevPage}
                    disabled={currentPage === 0}
                    className="p-2 text-chat-gray-600 hover:text-chat-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeftIcon className="w-5 h-5" />
                  </button>
                  <span className="text-sm text-chat-gray-600">
                    Page {currentPage + 1} of {totalPages}
                  </span>
                  <button
                    onClick={handleNextPage}
                    disabled={currentPage >= totalPages - 1}
                    className="p-2 text-chat-gray-600 hover:text-chat-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRightIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </>
          )}

          {loading && (
            <div className="text-center py-8">
              <div className="inline-block w-6 h-6 border-2 border-chat-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-2 text-sm text-chat-gray-600">Loading data...</p>
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
}

export default FileDataViewer