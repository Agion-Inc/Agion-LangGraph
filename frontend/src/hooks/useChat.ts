/**
 * Agent-Chat useChat Hook
 * Zustand store for chat state management with latest APIs
 */

import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type { ChatStore, ChatMessage, ChatSession } from '../types/chat'
import { chatHistoryApi } from '../services/api'

export const useChatStore = create<ChatStore>()(
  subscribeWithSelector((set, get) => ({
    // State
    sessions: [],
    activeSessionId: null,
    isLoading: false,
    error: null,

    // Actions
    loadSessions: async () => {
      try {
        const response = await chatHistoryApi.getSessions(1, 20)
        const loadedSessions: ChatSession[] = response.sessions.map(s => ({
          id: s.id,
          title: s.title,
          messages: [],
          createdAt: new Date(s.created_at),
          updatedAt: new Date(s.updated_at),
          isActive: true,
        }))

        set({ sessions: loadedSessions })

        // If no active session and we have sessions, set the first one as active
        if (!get().activeSessionId && loadedSessions.length > 0) {
          set({ activeSessionId: loadedSessions[0].id })
        }
      } catch (error) {
        console.error('Failed to load sessions:', error)
        set({ error: 'Failed to load chat history' })
      }
    },

    loadSessionMessages: async (sessionId: string) => {
      try {
        const response = await chatHistoryApi.getSessionMessages(sessionId, 1, 50)
        const messages: ChatMessage[] = response.messages.map(m => ({
          id: m.id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          timestamp: new Date(m.timestamp),
          status: 'sent' as const,
          agentId: m.agent_id,
          metadata: m.metadata,
        }))

        set(state => ({
          sessions: state.sessions.map(session =>
            session.id === sessionId
              ? { ...session, messages }
              : session
          ),
        }))
      } catch (error: any) {
        // 404 is expected for new sessions that don't have messages yet - not an error
        if (error?.response?.status === 404) {
          console.log(`Session ${sessionId} has no messages yet (new session)`)
          return
        }
        console.error('Failed to load messages:', error)
        set({ error: 'Failed to load messages' })
      }
    },

    createSession: () => {
      const sessionId = crypto.randomUUID()
      const newSession: ChatSession = {
        id: sessionId,
        title: 'New Chat',
        messages: [],
        createdAt: new Date(),
        updatedAt: new Date(),
        isActive: true,
      }

      set(state => ({
        sessions: [...state.sessions, newSession],
        activeSessionId: sessionId,
      }))

      return sessionId
    },

    deleteSession: async (sessionId: string) => {
      try {
        await chatHistoryApi.deleteSession(sessionId)

        set(state => ({
          sessions: state.sessions.filter(s => s.id !== sessionId),
          activeSessionId:
            state.activeSessionId === sessionId
              ? state.sessions.find(s => s.id !== sessionId)?.id || null
              : state.activeSessionId,
        }))
      } catch (error) {
        console.error('Failed to delete session:', error)
        set({ error: 'Failed to delete session' })
      }
    },


    renameSession: (sessionId: string, newTitle: string) => {
      set(state => ({
        sessions: state.sessions.map(session =>
          session.id === sessionId
            ? { ...session, title: newTitle, updatedAt: new Date() }
            : session
        ),
      }))
    },

    setActiveSession: (sessionId: string) => {
      set({ activeSessionId: sessionId })
    },

    addMessage: (sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
      const newMessage: ChatMessage = {
        ...message,
        id: crypto.randomUUID(),
        timestamp: new Date(),
      }

      set(state => ({
        sessions: state.sessions.map(session =>
          session.id === sessionId
            ? {
                ...session,
                messages: [...session.messages, newMessage],
                updatedAt: new Date(),
                title:
                  session.messages.length === 0 && message.role === 'user'
                    ? message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
                    : session.title,
              }
            : session
        ),
      }))
    },

    updateMessage: (sessionId: string, messageId: string, updates: Partial<ChatMessage>) => {
      set(state => ({
        sessions: state.sessions.map(session =>
          session.id === sessionId
            ? {
                ...session,
                messages: session.messages.map(message =>
                  message.id === messageId ? { ...message, ...updates } : message
                ),
                updatedAt: new Date(),
              }
            : session
        ),
      }))
    },

    clearMessages: (sessionId: string) => {
      set(state => ({
        sessions: state.sessions.map(session =>
          session.id === sessionId
            ? {
                ...session,
                messages: [],
                updatedAt: new Date(),
              }
            : session
        ),
      }))
    },

    setLoading: (loading: boolean) => {
      set({ isLoading: loading })
    },

    setError: (error: string | null) => {
      set({ error })
    },
  }))
)

// No longer auto-create sessions - they will be loaded from API or created explicitly