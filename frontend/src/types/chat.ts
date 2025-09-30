/**
 * Agent-Chat Frontend Types - Chat System
 * Type definitions for the chat interface and messaging system
 */

export interface ChatMessage {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  agentId?: string
  agentName?: string
  status?: 'sending' | 'sent' | 'error'
  metadata?: Record<string, any>
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: Date
  updatedAt: Date
  isActive: boolean
}

export interface ChatState {
  sessions: ChatSession[]
  activeSessionId: string | null
  isLoading: boolean
  error: string | null
}

export interface ChatActions {
  loadSessions: () => Promise<void>
  loadSessionMessages: (sessionId: string) => Promise<void>
  createSession: () => string
  deleteSession: (sessionId: string) => Promise<void>
  renameSession: (sessionId: string, newTitle: string) => void
  setActiveSession: (sessionId: string) => void
  addMessage: (sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  updateMessage: (sessionId: string, messageId: string, updates: Partial<ChatMessage>) => void
  clearMessages: (sessionId: string) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export type ChatStore = ChatState & ChatActions

export interface TypingIndicator {
  isVisible: boolean
  agentName?: string
  text: string
}