/**
 * AIRGB Main Chat Container
 * ChatGPT-inspired elegant chat interface
 */

import React, { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { MessageBubble } from './MessageBubble'
import { InputBox } from './InputBox'
import { TypingIndicator } from './TypingIndicator'
// import { AgentSelector } from './AgentSelector' // Removed - always use orchestrator
import { useChatStore } from '../../hooks/useChat'
import { useAgentStore } from '../../hooks/useAgents'
import type { ChatMessage } from '../../types/chat'
// import type { Agent } from '../../types/agents' // Not needed - using orchestrator

interface ChatContainerProps {
  className?: string
}

export const ChatContainer: React.FC<ChatContainerProps> = ({ className = '' }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [isInitialized, setIsInitialized] = useState(false)

  const {
    sessions,
    activeSessionId,
    addMessage,
    isLoading,
    error,
    setLoading,
    setError,
    loadSessions,
    loadSessionMessages
  } = useChatStore()

  const { invokeBestAgent, invokeAgent } = useAgentStore()

  const activeSession = sessions.find(s => s.id === activeSessionId)
  const messages = activeSession?.messages || []

  // Load sessions on mount
  useEffect(() => {
    const initializeChat = async () => {
      await loadSessions()
      setIsInitialized(true)
    }

    if (!isInitialized) {
      initializeChat()
    }
  }, [isInitialized, loadSessions])

  // Create a session if none exist after initialization
  useEffect(() => {
    if (isInitialized && sessions.length === 0 && !activeSessionId) {
      useChatStore.getState().createSession()
    }
  }, [isInitialized, sessions.length, activeSessionId])

  // Load messages when active session changes
  useEffect(() => {
    if (activeSessionId && activeSession && activeSession.messages.length === 0) {
      loadSessionMessages(activeSessionId)
    }
  }, [activeSessionId, activeSession, loadSessionMessages])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const handleSendMessage = async (content: string, files?: string[], agentId?: string) => {
    if (!activeSessionId || !content.trim()) return

    // Add user message immediately
    const userMessage: Omit<ChatMessage, 'id' | 'timestamp'> = {
      content: content.trim(),
      role: 'user',
      status: 'sent',
      agentId: agentId
    }

    addMessage(activeSessionId, userMessage)
    setLoading(true)
    setError(null)

    try {
      // Use the chat/send endpoint which saves to database and routes to agents
      const { chatHistoryApi } = await import('../../services/api')
      const response = await chatHistoryApi.sendMessage({
        message: content.trim(),
        session_id: activeSessionId,
        context: {},
        files: files || []
      })

      // Add assistant response
      const assistantMessage: Omit<ChatMessage, 'id' | 'timestamp'> = {
        content: response.message.content,
        role: 'assistant',
        status: 'sent',
        agentId: response.message.agent_id,
        agentName: response.message.agent_id?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        metadata: response.message.metadata
      }

      addMessage(activeSessionId, assistantMessage)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get response')

      // Add error message
      const errorMessage: Omit<ChatMessage, 'id' | 'timestamp'> = {
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        role: 'assistant',
        status: 'error'
      }

      addMessage(activeSessionId, errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`flex flex-col h-full bg-white ${className}`}>
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-chat mx-auto">
          {messages.map((message, index) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.3,
                ease: 'easeOut',
                delay: index * 0.05
              }}
            >
              <MessageBubble message={message} />
            </motion.div>
          ))}

          {/* Typing Indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <TypingIndicator />
            </motion.div>
          )}

          {/* Error Display */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className="p-4 mx-4 mb-4 bg-red-50 border border-red-200 rounded-lg"
            >
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
                <div className="ml-auto pl-3">
                  <button
                    onClick={() => setError(null)}
                    className="inline-flex text-red-400 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                  >
                    <span className="sr-only">Dismiss</span>
                    <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* Empty State */}
          {messages.length === 0 && !isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-col items-center justify-center h-96 text-center"
            >
              <div className="w-16 h-16 bg-chat-blue-100 rounded-full flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-chat-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-chat-gray-900 mb-2">
                Welcome to AIRGB
              </h3>
              <p className="text-chat-gray-500 max-w-md">
                Start a conversation by asking about your data, uploading files, or requesting analysis from our AI agents.
              </p>
            </motion.div>
          )}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white">
        <div className="max-w-chat mx-auto">
          {/* Agent Selector */}
          <div className="px-4 pb-2">
            {/* Agent selector removed - Orchestrator handles all routing */}
          </div>

          {/* Input Box */}
          <InputBox
            onSendMessage={handleSendMessage}
            disabled={isLoading}
            placeholder="Ask about your data, request analysis, or upload files..."
          />
        </div>
      </div>
    </div>
  )
}

export default ChatContainer
