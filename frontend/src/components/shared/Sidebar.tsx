/**
 * Agent-Chat Sidebar Component
 * Elegant file management and navigation with routing
 */

import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  FolderIcon, 
  DocumentIcon, 
  ChatBubbleLeftRightIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline'
import { useChatStore } from '../../hooks/useChat'
import { useFileStore } from '../../hooks/useFiles'
import { FileUploadZone } from '../upload/FileDropZone'

export const Sidebar: React.FC = () => {
  const location = useLocation()
  const { sessions, activeSessionId, createSession, setActiveSession, deleteSession, renameSession } = useChatStore()
  const { files, isUploading, error: uploadError } = useFileStore()
  const [editingSessionId, setEditingSessionId] = React.useState<string | null>(null)
  const [editingSessionTitle, setEditingSessionTitle] = React.useState<string>('')
  const [uploadSuccess, setUploadSuccess] = React.useState<string | null>(null)
  const [lastFileCount, setLastFileCount] = React.useState(files.length)

  const handleNewChat = () => {
    createSession()
  }

  const handleStartRename = (sessionId: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingSessionId(sessionId)
    setEditingSessionTitle(currentTitle)
  }

  const handleFinishRename = (sessionId: string) => {
    if (editingSessionTitle.trim() && editingSessionTitle !== sessions.find(s => s.id === sessionId)?.title) {
      renameSession(sessionId, editingSessionTitle.trim())
    }
    setEditingSessionId(null)
    setEditingSessionTitle('')
  }

  const handleCancelRename = () => {
    setEditingSessionId(null)
    setEditingSessionTitle('')
  }

  const isActive = (path: string) => location.pathname === path

  // Monitor file uploads for success/failure
  React.useEffect(() => {
    if (files.length > lastFileCount) {
      // New file(s) added
      const newFilesCount = files.length - lastFileCount
      setUploadSuccess(`Successfully uploaded ${newFilesCount} file${newFilesCount > 1 ? 's' : ''}`)
      setTimeout(() => setUploadSuccess(null), 5000) // Clear after 5 seconds
    }
    setLastFileCount(files.length)
  }, [files.length, lastFileCount])

  // Clear success message when upload error occurs
  React.useEffect(() => {
    if (uploadError) {
      setUploadSuccess(null)
    }
  }, [uploadError])

  return (
    <div className="h-full flex flex-col bg-chat-gray-50">
      {/* Header with Navigation */}
      <div className="p-4 border-b border-chat-gray-200">
        <button
          onClick={handleNewChat}
          className="w-full bg-white border border-chat-gray-300 rounded-lg px-4 py-2 text-sm font-medium text-chat-gray-700 hover:bg-chat-gray-50 focus:outline-none focus:ring-2 focus:ring-chat-blue-500 focus:ring-offset-2 transition-colors duration-200 flex items-center justify-center"
        >
          <ChatBubbleLeftRightIcon className="w-4 h-4 mr-2" />
          New Chat
        </button>

        {/* Navigation Links */}
        <div className="mt-3 space-y-1">
          <Link
            to="/chat"
            className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive('/chat')
                ? 'bg-chat-blue-100 text-chat-blue-900'
                : 'text-chat-gray-700 hover:bg-white'
            }`}
          >
            <ChatBubbleLeftRightIcon className="w-4 h-4 mr-2" />
            Chat
          </Link>
          <Link
            to="/files"
            className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive('/files')
                ? 'bg-chat-blue-100 text-chat-blue-900'
                : 'text-chat-gray-700 hover:bg-white'
            }`}
          >
            <FolderIcon className="w-4 h-4 mr-2" />
            Files
            {files.length > 0 && (
              <span className="ml-auto bg-chat-blue-600 text-white text-xs px-2 py-0.5 rounded-full">
                {files.length}
              </span>
            )}
          </Link>
          <Link
            to="/agents"
            className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive('/agents')
                ? 'bg-chat-blue-100 text-chat-blue-900'
                : 'text-chat-gray-700 hover:bg-white'
            }`}
          >
            <CpuChipIcon className="w-4 h-4 mr-2" />
            Agents
          </Link>
        </div>
      </div>

      {/* File Upload Area */}
      <div className="p-4 border-b border-chat-gray-200">
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-chat-gray-900 flex items-center">
            <DocumentIcon className="w-4 h-4 mr-2" />
            Upload Files
          </h3>
        </div>
        <FileUploadZone />
        
        {/* Upload Status Banner */}
        {(uploadSuccess || uploadError || isUploading) && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-3"
          >
            {isUploading && (
              <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
                <span className="text-xs text-blue-800 font-medium">Uploading files...</span>
              </div>
            )}
            
            {uploadSuccess && !isUploading && (
              <div className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg">
                <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-xs text-green-800 font-medium">{uploadSuccess}</span>
              </div>
            )}
            
            {uploadError && !isUploading && (
              <div className="flex items-start gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
                <svg className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <div className="flex-1 min-w-0">
                  <span className="text-xs text-red-800 font-medium block">Upload failed</span>
                  <span className="text-xs text-red-600">{uploadError}</span>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>

      {/* Chat Sessions */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-chat-gray-900">Recent Chats</h3>
        </div>
        <div className="space-y-1">
          {sessions.map(session => (
            <motion.button
              key={session.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              onClick={() => setActiveSession(session.id)}
              className={`w-full text-left p-3 rounded-lg text-sm transition-colors duration-200 group ${
                activeSessionId === session.id
                  ? 'bg-chat-blue-100 text-chat-blue-900'
                  : 'text-chat-gray-700 hover:bg-white'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  {editingSessionId === session.id ? (
                    <input
                      type="text"
                      value={editingSessionTitle}
                      onChange={(e) => setEditingSessionTitle(e.target.value)}
                      onBlur={() => handleFinishRename(session.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleFinishRename(session.id)
                        } else if (e.key === 'Escape') {
                          handleCancelRename()
                        }
                        e.stopPropagation()
                      }}
                      onClick={(e) => e.stopPropagation()}
                      autoFocus
                      className="w-full font-medium bg-white border border-blue-500 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  ) : (
                    <div 
                      className="font-medium truncate cursor-pointer hover:text-chat-blue-600 transition-colors"
                      onClick={(e) => handleStartRename(session.id, session.title, e)}
                      title="Click to rename"
                    >
                      {session.title}
                    </div>
                  )}
                  <div className="text-xs text-chat-gray-500 mt-1">
                    {session.messages.length} messages
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteSession(session.id)
                  }}
                  className="opacity-0 group-hover:opacity-100 text-chat-gray-400 hover:text-red-600 transition-opacity"
                  title="Delete chat"
                >
                  ×
                </button>
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Footer with Copyright */}
      <div className="p-4 border-t border-chat-gray-200 bg-chat-gray-50">
        <div className="text-xs text-chat-gray-600 text-center">
          © 2025 Agion
        </div>
      </div>
    </div>
  )
}

export default Sidebar
