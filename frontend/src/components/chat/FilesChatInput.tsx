/**
 * Files Chat Input Component
 * Shared chat input for Files view that preserves state
 */

import React from 'react'
import { useNavigate } from 'react-router-dom'
import { InputBox } from './InputBox'
import { useChatStore } from '../../hooks/useChat'
import { useAgentStore } from '../../hooks/useAgents'
import type { ChatMessage } from '../../types/chat'

export const FilesChatInput: React.FC = () => {
  const navigate = useNavigate()
  const {
    activeSessionId,
    addMessage,
    isLoading,
    setLoading,
    setError
  } = useChatStore()

  const { invokeBestAgent, invokeAgent } = useAgentStore()

  const handleSendMessage = async (content: string, files?: string[], agentId?: string) => {
    if (!activeSessionId || !content.trim()) return
    
    // Navigate to chat view immediately after sending
    navigate('/chat')

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
      let response
      
      if (agentId) {
        // Use specific agent if selected
        response = await invokeAgent(agentId, {
          user_query: content,
          context: {},
          files: files || [],
          parameters: {},
          priority: 1
        })
      } else {
        // Use the orchestrator (invokeBestAgent) for intelligent routing
        response = await invokeBestAgent(content, {}, files)
      }

      // Add assistant response
      const assistantMessage: Omit<ChatMessage, 'id' | 'timestamp'> = {
        content: response.message,
        role: 'assistant',
        status: 'sent',
        agentId: response.agent_id,
        agentName: response.agent_id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        metadata: {
          confidence: response.confidence,
          executionTime: response.execution_time,
          nextSuggestions: response.next_suggestions,
          data: response.data
        }
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
    <div className="bg-white border-t border-chat-gray-200">
      <div className="max-w-chat mx-auto">
        <InputBox
          onSendMessage={handleSendMessage}
          disabled={isLoading}
          placeholder="Tag files with @ or ask questions about your data..."
        />
      </div>
    </div>
  )
}

export default FilesChatInput
