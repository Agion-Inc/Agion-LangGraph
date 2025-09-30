/**
 * Agent-Chat Input Box Component  
 * Elegant message input with @-tag file references and autocomplete
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { PaperAirplaneIcon, XMarkIcon, DocumentIcon, CpuChipIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { useFileStore } from '../../hooks/useFiles'
import { useAgentStore } from '../../hooks/useAgents'
import { useChatInputState } from '../../hooks/useChatInputState'

interface InputBoxProps {
  onSendMessage: (message: string, files?: string[], agentId?: string) => void
  disabled?: boolean
  placeholder?: string
}

export const InputBox: React.FC<InputBoxProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = 'Type @ to mention files or agents...',
}) => {
  // Use shared state for persistence between views
  const {
    message,
    mentionedFiles,
    isComposing,
    setMessage,
    setMentionedFiles,
    setIsComposing,
    addMentionedFile,
    removeMentionedFile,
    clearInput
  } = useChatInputState()

  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [autocompleteQuery, setAutocompleteQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [autocompleteType, setAutocompleteType] = useState<'all' | 'files' | 'agents'>('all')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const autocompleteRef = useRef<HTMLDivElement>(null)
  const { files } = useFileStore()
  const { agents, loadAgents } = useAgentStore()

  // Include all files except those that are still uploading
  // This makes files available as soon as they're uploaded, even if processing isn't complete
  const completedFiles = files.filter(f => 
    f.status !== 'uploading' && f.status !== 'pending'
  )

  // Load agents on mount
  useEffect(() => {
    if (agents.length === 0) {
      loadAgents().catch(() => {
        // Silently handle error
      })
    }
  }, [])

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = '48px'
      const scrollHeight = textarea.scrollHeight
      const maxHeight = 200
      const newHeight = Math.min(scrollHeight, maxHeight)
      textarea.style.height = newHeight + 'px'
      textarea.style.overflowY = scrollHeight > maxHeight ? 'auto' : 'hidden'
    }
  }, [message])

  // Handle @ detection for autocomplete
  const checkForAtMention = useCallback(() => {
    const cursorPosition = textareaRef.current?.selectionStart || 0
    const textBeforeCursor = message.slice(0, cursorPosition)
    const atMatch = textBeforeCursor.match(/@(\w*)$/)
    
    console.log('Checking for @ mention:', { 
      cursorPosition, 
      textBeforeCursor, 
      atMatch, 
      message,
      completedFiles: completedFiles.length,
      agents: agents.length 
    })
    
    if (atMatch) {
      const query = atMatch[1] || ''
      setAutocompleteQuery(query.toLowerCase())
      setShowAutocomplete(true)
      setSelectedIndex(0)
    } else {
      setShowAutocomplete(false)
      setAutocompleteQuery('')
    }
  }, [message, completedFiles.length, agents.length])

  // Check for @ mention when message changes
  useEffect(() => {
    checkForAtMention()
  }, [checkForAtMention])

  // Filter files and agents for autocomplete
  // Add mock data for testing if no real data exists
  const availableFiles = completedFiles.length > 0 ? completedFiles : []
  const availableAgents = agents.length > 0 ? agents : []
  
  const filteredFiles = availableFiles.filter(file =>
    file.name.toLowerCase().includes(autocompleteQuery.toLowerCase())
  )

  const filteredAgents = availableAgents.filter(agent =>
    agent.name.toLowerCase().includes(autocompleteQuery.toLowerCase()) ||
    agent.description.toLowerCase().includes(autocompleteQuery.toLowerCase())
  )

  // Combine items for display
  const allItems = [
    ...filteredFiles.map(f => ({ type: 'file' as const, item: f })),
    ...filteredAgents.map(a => ({ type: 'agent' as const, item: a }))
  ]

  const displayItems = autocompleteType === 'all' ? allItems :
    autocompleteType === 'files' ? filteredFiles.map(f => ({ type: 'file' as const, item: f })) :
    filteredAgents.map(a => ({ type: 'agent' as const, item: a }))

  // Handle keyboard navigation in autocomplete
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showAutocomplete && displayItems.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex(prev => Math.min(prev + 1, displayItems.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex(prev => Math.max(prev - 1, 0))
        return
      }
      if (e.key === 'Tab' || e.key === 'Enter') {
        if (showAutocomplete) {
          e.preventDefault()
          const selected = displayItems[selectedIndex]
          if (selected.type === 'file') {
            insertFileReference(selected.item)
          } else {
            insertAgentReference(selected.item)
          }
          return
        }
      }
      if (e.key === 'Escape') {
        setShowAutocomplete(false)
        return
      }
    }

    if (e.key === 'Enter' && !e.shiftKey && !showAutocomplete) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // Insert file reference
  const insertFileReference = (file: { id: string; name: string }) => {
    const cursorPosition = textareaRef.current?.selectionStart || 0
    const textBeforeCursor = message.slice(0, cursorPosition)
    const textAfterCursor = message.slice(cursorPosition)
    
    // Replace the @query with @filename
    const atMatch = textBeforeCursor.match(/@(\w*)$/)
    if (atMatch) {
      const beforeAt = textBeforeCursor.slice(0, -atMatch[0].length)
      const newMessage = `${beforeAt}@file:${file.name} ${textAfterCursor}`
      setMessage(newMessage)
      
      // Track mentioned file using shared state
      addMentionedFile({
        id: file.id,
        name: file.name,
        position: beforeAt.length
      })
      
      setShowAutocomplete(false)
      
      // Set cursor after the mention
      setTimeout(() => {
        const newPosition = beforeAt.length + file.name.length + 7 // @file: + name + space
        textareaRef.current?.setSelectionRange(newPosition, newPosition)
        textareaRef.current?.focus()
      }, 0)
    }
  }

  // Insert agent reference
  const insertAgentReference = (agent: { agent_id: string; name: string }) => {
    const cursorPosition = textareaRef.current?.selectionStart || 0
    const textBeforeCursor = message.slice(0, cursorPosition)
    const textAfterCursor = message.slice(cursorPosition)
    
    // Replace the @query with @agent:name
    const atMatch = textBeforeCursor.match(/@(\w*)$/)
    if (atMatch) {
      const beforeAt = textBeforeCursor.slice(0, -atMatch[0].length)
      const newMessage = `${beforeAt}@agent:${agent.name} ${textAfterCursor}`
      setMessage(newMessage)
      
      // Track selected agent
      setSelectedAgent(agent.agent_id)
      
      setShowAutocomplete(false)
      
      // Set cursor after the mention
      setTimeout(() => {
        const newPosition = beforeAt.length + agent.name.length + 8 // @agent: + name + space
        textareaRef.current?.setSelectionRange(newPosition, newPosition)
        textareaRef.current?.focus()
      }, 0)
    }
  }

  // Remove file mention using shared state
  const removeMention = (fileId: string) => {
    removeMentionedFile(fileId)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || disabled || isComposing) return

    // Extract file IDs from mentioned files
    const fileIds = mentionedFiles.map(m => m.id)

    onSendMessage(
      message.trim(), 
      fileIds.length > 0 ? fileIds : undefined,
      selectedAgent || undefined
    )
    clearInput()
    setSelectedAgent(null)
  }

  const canSend = message.trim().length > 0 && !disabled && !isComposing

  return (
    <motion.div
      className="p-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut'}}
    >
      {/* Mentioned Files Preview */}
      {mentionedFiles.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mb-3 p-3 bg-chat-blue-50 rounded-lg border border-chat-blue-200"
        >
          <div className="text-xs text-chat-blue-900 mb-2 font-medium flex items-center">
            <DocumentIcon className="w-4 h-4 mr-1" />
            Referenced files ({mentionedFiles.length}):
          </div>
          <div className="flex flex-wrap gap-2">
            {mentionedFiles.map(mention => {
              const file = files.find(f => f.id === mention.id)
              return file ? (
                <div
                  key={mention.id}
                  className="flex items-center px-3 py-1.5 bg-white rounded-lg border border-chat-blue-300 text-sm"
                >
                  <DocumentIcon className="w-4 h-4 mr-2 text-chat-blue-600" />
                  <span className="font-medium">{file.name}</span>
                  <button
                    onClick={() => removeMention(mention.id)}
                    className="ml-2 text-chat-gray-400 hover:text-red-600"
                  >
                    <XMarkIcon className="w-4 h-4" />
                  </button>
                </div>
              ) : null
            })}
          </div>
        </motion.div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex items-start space-x-3">
          {/* Text Input with Autocomplete */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => {
                setMessage(e.target.value)
                // Check for @ mention immediately after typing
                setTimeout(() => checkForAtMention(), 0)
              }}
              onKeyUp={() => {
                // Also check on key up to catch cursor movement
                checkForAtMention()
              }}
              onMouseUp={() => {
                // Check when clicking to move cursor
                checkForAtMention()
              }}
              onKeyDown={handleKeyDown}
              onCompositionStart={() => setIsComposing(true)}
              onCompositionEnd={() => setIsComposing(false)}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className="w-full resize-none border border-chat-gray-300 rounded-lg px-4 focus:outline-none focus:ring-2 focus:ring-chat-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed text-chat-gray-900 placeholder-chat-gray-500 bg-white overflow-hidden"
              style={{ minHeight: '48px', maxHeight: '200px', paddingTop: '12px', paddingBottom: '12px' }}
            />

            {/* Autocomplete Dropdown - Enhanced for Files and Agents */}
            {showAutocomplete && (
              <motion.div
                ref={autocompleteRef}
                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-xl shadow-2xl border border-chat-gray-300 max-h-80 overflow-hidden z-50"
                style={{ boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)' }}
              >
                <div className="overflow-y-auto max-h-80">
                  {/* Tab Selector */}
                  <div className="flex border-b border-chat-gray-200 bg-chat-gray-50">
                    <button
                      type="button"
                      onClick={() => setAutocompleteType('all')}
                      className={`flex-1 px-3 py-2 text-xs font-semibold transition-colors ${
                        autocompleteType === 'all'
                          ? 'text-chat-blue-600 border-b-2 border-chat-blue-600 bg-white'
                          : 'text-chat-gray-600 hover:text-chat-gray-900'
                      }`}
                    >
                      All
                    </button>
                    <button
                      type="button"
                      onClick={() => setAutocompleteType('files')}
                      className={`flex-1 px-3 py-2 text-xs font-semibold transition-colors ${
                        autocompleteType === 'files'
                          ? 'text-chat-blue-600 border-b-2 border-chat-blue-600 bg-white'
                          : 'text-chat-gray-600 hover:text-chat-gray-900'
                      }`}
                    >
                      Files ({filteredFiles.length})
                    </button>
                    <button
                      type="button"
                      onClick={() => setAutocompleteType('agents')}
                      className={`flex-1 px-3 py-2 text-xs font-semibold transition-colors ${
                        autocompleteType === 'agents'
                          ? 'text-chat-blue-600 border-b-2 border-chat-blue-600 bg-white'
                          : 'text-chat-gray-600 hover:text-chat-gray-900'
                      }`}
                    >
                      Agents ({filteredAgents.length})
                    </button>
                  </div>

                  {/* Items List */}
                  <div className="py-1">
                    {displayItems.map((entry, index) => (
                      entry.type === 'file' ? (
                        <button
                          key={entry.item.id}
                          type="button"
                          onClick={() => insertFileReference(entry.item)}
                          onMouseEnter={() => setSelectedIndex(index)}
                          className={`w-full text-left px-4 py-2.5 transition-colors flex items-center gap-3 ${
                            index === selectedIndex
                              ? 'bg-chat-blue-50 text-chat-blue-900'
                              : 'hover:bg-chat-gray-50 text-chat-gray-800'
                          }`}
                        >
                          <div className={`flex-shrink-0 w-8 h-8 rounded flex items-center justify-center ${
                            index === selectedIndex ? 'bg-chat-blue-100' : 'bg-chat-gray-100'
                          }`}>
                            <DocumentIcon className={`w-5 h-5 ${
                              index === selectedIndex ? 'text-chat-blue-600' : 'text-chat-gray-600'
                            }`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate text-sm">
                              <span className="text-xs text-chat-gray-500 mr-1">file:</span>
                              {entry.item.name}
                            </div>
                            <div className="text-xs text-chat-gray-500 mt-0.5">
                              {(entry.item.size / 1024).toFixed(1)} KB • {entry.item.status}
                            </div>
                          </div>
                          {index === selectedIndex && (
                            <div className="text-xs font-mono text-chat-blue-600 bg-chat-blue-100 px-2 py-1 rounded">
                              ↵
                            </div>
                          )}
                        </button>
                      ) : (
                        <button
                          key={entry.item.agent_id}
                          type="button"
                          onClick={() => insertAgentReference(entry.item)}
                          onMouseEnter={() => setSelectedIndex(index)}
                          className={`w-full text-left px-4 py-2.5 transition-colors flex items-center gap-3 ${
                            index === selectedIndex
                              ? 'bg-chat-purple-50 text-chat-purple-900'
                              : 'hover:bg-chat-gray-50 text-chat-gray-800'
                          }`}
                        >
                          <div className={`flex-shrink-0 w-8 h-8 rounded flex items-center justify-center ${
                            index === selectedIndex ? 'bg-chat-purple-100' : 'bg-chat-gray-100'
                          }`}>
                            <CpuChipIcon className={`w-5 h-5 ${
                              index === selectedIndex ? 'text-chat-purple-600' : 'text-chat-gray-600'
                            }`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate text-sm">
                              <span className="text-xs text-chat-purple-500 mr-1">agent:</span>
                              {entry.item.name}
                            </div>
                            <div className="text-xs text-chat-gray-500 mt-0.5">
                              {entry.item.description}
                            </div>
                            <div className="flex gap-1 mt-1">
                              {entry.item.capabilities.slice(0, 2).map((cap: string) => (
                                <span key={cap} className="px-1.5 py-0.5 text-xs bg-chat-purple-100 text-chat-purple-700 rounded">
                                  {cap.replace('_', ' ')}
                                </span>
                              ))}
                            </div>
                          </div>
                          {index === selectedIndex && (
                            <div className="text-xs font-mono text-chat-purple-600 bg-chat-purple-100 px-2 py-1 rounded">
                              ↵
                            </div>
                          )}
                        </button>
                      )
                    ))}

                    {displayItems.length === 0 && (
                      <div className="px-4 py-6 text-center text-sm text-chat-gray-500">
                        {completedFiles.length === 0 && agents.length === 0 ? (
                          <div>
                            <p className="font-medium mb-2">No files or agents available</p>
                            <p className="text-xs">Upload files or wait for agents to load to use @ mentions</p>
                          </div>
                        ) : (
                          <>
                            {autocompleteType === 'all' ? 'No files or agents found' :
                             autocompleteType === 'files' ? 'No files found' :
                             'No agents found'}
                            {autocompleteQuery && ` matching "${autocompleteQuery}"`}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Footer with hint */}
                <div className="px-4 py-2 bg-chat-gray-50 border-t border-chat-gray-200">
                  <div className="text-xs text-chat-gray-500">
                    <kbd className="px-1.5 py-0.5 bg-white border border-chat-gray-300 rounded text-xs font-mono">↑</kbd>
                    <kbd className="ml-1 px-1.5 py-0.5 bg-white border border-chat-gray-300 rounded text-xs font-mono">↓</kbd>
                    <span className="ml-1">to navigate</span>
                    <kbd className="ml-2 px-1.5 py-0.5 bg-white border border-chat-gray-300 rounded text-xs font-mono">↵</kbd>
                    <span className="ml-1">to select</span>
                    <kbd className="ml-2 px-1.5 py-0.5 bg-white border border-chat-gray-300 rounded text-xs font-mono">esc</kbd>
                    <span className="ml-1">to dismiss</span>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Character count */}
            {message.length > 1000 && (
              <div className="absolute bottom-1 right-1 text-xs text-chat-gray-400">
                {message.length}/2000
              </div>
            )}
          </div>

          {/* Send Button */}
          <motion.button
            type="submit"
            disabled={!canSend}
            className={`p-3 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-chat-blue-500 focus:ring-offset-2 flex-shrink-0 ${
              canSend
                ? 'bg-chat-blue-600 hover:bg-chat-blue-700 text-white'
                : 'bg-chat-gray-200 text-chat-gray-400 cursor-not-allowed'
            }`}
            style={{ height: '48px', width: '48px' }}
            whileHover={canSend ? { scale: 1.05 } : {}}
            whileTap={canSend ? { scale: 0.95 } : {}}
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </motion.button>
        </div>

        {/* Hints */}
        <div className="mt-2 text-xs text-chat-gray-500 flex items-center justify-between">
          <div>
            Press Enter to send, Shift+Enter for new line
            <span className="ml-4">• Type @ to reference files or agents</span>
          </div>
          <div className="flex items-center space-x-4">
            {disabled && <span>Processing...</span>}
            {files.some(f => f.status === 'uploading') && (
              <span className="text-chat-blue-600">Uploading files...</span>
            )}
          </div>
        </div>
      </form>
    </motion.div>
  )
}

export default InputBox
